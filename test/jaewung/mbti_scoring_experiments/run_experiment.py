from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import importlib
import json
import os
from pathlib import Path
import re
from statistics import pstdev
import sys
import uuid

from stability import summarize_strategy, write_dashboard
from strategies import ExperimentCase, build_strategies


BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parents[2]
BACKEND_DIR = REPO_ROOT / "app" / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

STRATEGY_DIRS = {
    "persona_direct": BASE_DIR / "single_llm" / "01_persona_direct",
    "rubric_code": BASE_DIR / "single_llm" / "02_rubric_code",
    "triple_majority": BASE_DIR / "multi_llm" / "03_triple_majority",
    "hundred_point_ensemble": BASE_DIR / "multi_llm" / "04_hundred_point_ensemble",
    "triple_supervisor": BASE_DIR / "multi_llm" / "05_triple_supervisor",
}

AXIS_ORDER = ("IE", "SN", "TF", "JP")
DEFAULT_SCORING_TEMPERATURE = 0.0
DEFAULT_SCORING_MAX_OUTPUT_TOKENS = 1200

CONTROL_STRATEGY = "persona_direct"
CONTROL_COMBO = "single_1_openai_baseline"
CURRENT_DEMO_DATASET = "demo_questions_v4_jp_mixed_j_rebalanced_20260703"
CURRENT_RUN_BATCH = (
    os.getenv("MBTI_EXPERIMENT_RUN_BATCH")
    or "v5_persona_prompt_unified_no_random_20260704_01"
)
RESULT_SET_NAME = (
    os.getenv("MBTI_EXPERIMENT_RESULT_SET")
    or "persona_prompt_unified_no_random_20260704"
)
RESULT_FILE_NAME = f"mbti_score_changes_{RESULT_SET_NAME}.csv"
SUMMARY_FILE_NAME = f"stability_summary_{RESULT_SET_NAME}.csv"
REPORT_FILE_NAME = f"STABILITY_REPORT_{RESULT_SET_NAME}.md"
DASHBOARD_FILE_NAME = f"STABILITY_DASHBOARD_{RESULT_SET_NAME}.md"
PROMPT_VERSIONS = {
    "persona_direct": "persona_py_prompt_source_v1_20260704",
    "rubric_code": "rubric_code_prompt_v1",
    "triple_majority": "placeholder_prompt_na",
    "hundred_point_ensemble": "placeholder_prompt_na",
    "triple_supervisor": "persona_py_triple_supervisor_v1_20260704",
}


def _env(name: str, default: str) -> str:
    return os.getenv(name) or default


EXPERIMENT_COMBOS = {
    "single_1_openai_baseline": {
        "description": "Single-model control: current OpenAI baseline service candidate.",
        "provider": _env("MBTI_SINGLE_1_PROVIDER", "openai"),
        "model": _env("MBTI_SINGLE_1_MODEL", "gpt-5.4-mini"),
        "judges": (),
        "supervisor": None,
    },
    "single_2_groq_qwen": {
        "description": "Single-model experiment: Groq Qwen comparison candidate.",
        "provider": _env("MBTI_SINGLE_2_PROVIDER", "groq"),
        "model": _env("MBTI_SINGLE_2_MODEL", "qwen/qwen3-32b"),
        "judges": (),
        "supervisor": None,
    },
}


@dataclass(frozen=True)
class ExperimentScoringConfig:
    provider: str
    model: str
    temperature: float = DEFAULT_SCORING_TEMPERATURE
    max_output_tokens: int = DEFAULT_SCORING_MAX_OUTPUT_TOKENS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run backend monthly MBTI pipeline experiments."
    )
    parser.add_argument(
        "--use-persona-llm",
        action="store_true",
        help=(
            "Run persona_direct through the existing app/backend MBTI scoring "
            "client. This may call an external LLM API."
        ),
    )
    parser.add_argument(
        "--use-rubric-llm",
        action="store_true",
        help=(
            "Run rubric_code with the experiment rubric_code-only prompt and "
            "docs/한재웅/datasets/mbti_scoring_rubrics.v1.json. This may call "
            "an external LLM API."
        ),
    )
    parser.add_argument(
        "--use-triple-supervisor-llm",
        action="store_true",
        help=(
            "Run triple_supervisor with three persona-direct LLM scoring calls "
            "and a deterministic supervisor. This may call external LLM APIs."
        ),
    )
    parser.add_argument(
        "--strategy",
        choices=tuple(STRATEGY_DIRS),
        help="Run only one scoring strategy and write results under its folder.",
    )
    parser.add_argument(
        "--combo",
        choices=tuple(EXPERIMENT_COMBOS),
        help="Record one of the recommended provider/model experiment combinations.",
    )
    parser.add_argument(
        "--provider",
        help="Override the single scoring provider recorded for this run.",
    )
    parser.add_argument(
        "--model",
        help="Override the single scoring model recorded for this run.",
    )
    return parser.parse_args()


class StrategyScoringClient:
    """Adapter from experiment strategies to the real backend scoring client shape."""

    def __init__(self, strategy) -> None:
        self.strategy = strategy

    def score_axis_responses(self, *, axis, responses, config):
        scores = []
        for response in responses:
            prediction = self.strategy.score(
                ExperimentCase(
                    case_id=str(response.id),
                    axis=axis,
                    question=response.question_text,
                    answer=response.answer_text,
                )
            )
            scores.append(
                {
                    "response_id": response.id,
                    "score": prediction.predicted_score,
                    "coding_status": prediction.predicted_status,
                    "reason": prediction.reason,
                }
            )
        return {"scores": scores}


class PersonaDirectLlmScoringClient:
    def score_axis_responses(self, *, axis, responses, config):
        from mbti.services.response_scoring import (
            build_axis_scoring_input,
            build_axis_scoring_system_prompt,
        )

        content = _openai_compatible_chat_content(
            provider=config.provider,
            model=config.model,
            system_prompt=build_axis_scoring_system_prompt(),
            user_prompt=build_axis_scoring_input(axis=axis, responses=responses),
            temperature=config.temperature,
            max_tokens=config.max_output_tokens,
        )
        try:
            return _extract_json_object(str(content))
        except json.JSONDecodeError as exc:
            return _build_failed_scoring_payload(
                responses=responses,
                reason=f"LLM returned invalid JSON: {exc}",
            )


def _build_scoring_config(
    *,
    provider: str | None,
    model: str | None,
) -> ExperimentScoringConfig:
    selected_provider = (provider or os.getenv("MBTI_SCORING_PROVIDER") or "openai").lower()
    model_env_by_provider = {
        "openai": ("MBTI_OPENAI_SCORING_MODEL", "gpt-5.4-mini"),
        "groq": ("MBTI_GROQ_SCORING_MODEL", "qwen/qwen3-32b"),
        "google": ("MBTI_GEMINI_SCORING_MODEL", "gemini-2.5-flash"),
        "gemini": ("MBTI_GEMINI_SCORING_MODEL", "gemini-2.5-flash"),
    }
    model_env, default_model = model_env_by_provider.get(
        selected_provider,
        ("MBTI_SCORING_MODEL", "gpt-5.4-mini"),
    )
    selected_model = (
        model
        or os.getenv(model_env)
        or os.getenv("MBTI_SCORING_MODEL")
        or default_model
    )
    return ExperimentScoringConfig(
        provider=selected_provider,
        model=selected_model,
    )


def _openai_compatible_chat_content(
    *,
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    provider_key = provider.lower()
    if provider_key == "groq":
        api_key = os.getenv("GROQ_API_KEY")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    elif provider_key in {"google", "gemini"}:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        base_url = os.getenv(
            "GEMINI_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        )
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

    if provider_key != "openai" and not api_key:
        raise ValueError(f"{provider} API key is not configured.")

    return _langchain_openai_chat_content(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
    )


def _langchain_openai_chat_content(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    api_key: str | None = None,
    base_url: str | None = None,
) -> str:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        missing = exc.name or "langchain dependency"
        raise ModuleNotFoundError(
            f"{missing} is required for OpenAI experiments. "
            "Install app/backend/requirements.txt in the Python environment "
            "used to run this script."
        ) from exc

    llm_kwargs = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_key:
        llm_kwargs["api_key"] = api_key
    if base_url:
        llm_kwargs["base_url"] = base_url

    llm = ChatOpenAI(
        **llm_kwargs,
    )
    message = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    content = message.content
    if isinstance(content, list):
        return "".join(
            str(item.get("text", item)) if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content or "")


def _json_loads_lenient(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        escaped_invalid_backslashes = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', text)
        if escaped_invalid_backslashes == text:
            raise
        return json.loads(escaped_invalid_backslashes)


def _extract_json_object(text: str):
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        return _json_loads_lenient(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}") + 1
        if start < 0 or end <= start:
            raise
        return _json_loads_lenient(stripped[start:end])


def _build_failed_scoring_payload(*, responses, reason: str) -> dict[str, object]:
    return {
        "scores": [
            {
                "response_id": response.id,
                "score": None,
                "coding_status": "failed",
                "reason": reason,
            }
            for response in responses
        ]
    }


def _display_score(axis_result) -> int | None:
    selected = axis_result.selected_letter
    ratios = axis_result.axis_ratios or {}
    if selected and selected in ratios:
        return round(float(ratios[selected]) * 100)
    return None


def _previous_display_score(axis_result) -> int | None:
    selected = axis_result.baseline_letter
    ratios = axis_result.previous_axis_ratios or {}
    if selected and selected in ratios:
        return round(float(ratios[selected]) * 100)
    return None


def _axis_delta(axis_result) -> int | None:
    previous = _previous_display_score(axis_result)
    current = _display_score(axis_result)
    if previous is None or current is None:
        return None
    return current - previous


def _changed_preferences(previous_type: str | None, current_type: str | None) -> str:
    if not previous_type or not current_type:
        return ""
    index_by_axis = {"IE": 0, "SN": 1, "TF": 2, "JP": 3}
    changes = []
    for axis in AXIS_ORDER:
        index = index_by_axis[axis]
        if previous_type[index] != current_type[index]:
            changes.append(f"{axis}:{previous_type[index]}->{current_type[index]}")
    return "; ".join(changes)


def _model_label(provider: str | None, model: str | None) -> str:
    if not provider and not model:
        return ""
    if not provider:
        return str(model or "")
    if not model:
        return str(provider)
    return f"{provider}:{model}"


def _env_model_label(provider_key: str, model_key: str) -> str:
    return _model_label(os.getenv(provider_key), os.getenv(model_key))


def _judge_models_from_env() -> str:
    labels = [
        _env_model_label(f"MBTI_JUDGE_{index}_PROVIDER", f"MBTI_JUDGE_{index}_MODEL")
        for index in range(1, 4)
    ]
    return "; ".join(label for label in labels if label)


def _supervisor_model_from_env() -> str:
    return _env_model_label("MBTI_SUPERVISOR_PROVIDER", "MBTI_SUPERVISOR_MODEL")


def _combo_metadata(combo_name: str | None) -> dict[str, object]:
    if not combo_name:
        return {
            "experiment_combo": "",
            "combo_description": "",
            "combo_judge_models": "",
            "combo_supervisor_model": "",
        }
    combo = EXPERIMENT_COMBOS[combo_name]
    judges = "; ".join(_model_label(provider, model) for provider, model in combo["judges"])
    supervisor = combo["supervisor"]
    return {
        "experiment_combo": combo_name,
        "combo_description": combo["description"],
        "combo_judge_models": judges,
        "combo_supervisor_model": (
            _model_label(supervisor[0], supervisor[1]) if supervisor else ""
        ),
    }


def _experiment_family(strategy_name: str) -> str:
    return "single_llm" if strategy_name in {"persona_direct", "rubric_code"} else "multi_llm"


def _experiment_group(*, strategy_name: str, combo_name: str | None) -> str:
    if strategy_name == CONTROL_STRATEGY and combo_name == CONTROL_COMBO:
        return "control"
    return "experiment"


def _experiment_variable(*, strategy_name: str, combo_name: str | None) -> str:
    if strategy_name == CONTROL_STRATEGY and combo_name == CONTROL_COMBO:
        return "baseline"
    if strategy_name == CONTROL_STRATEGY:
        return "model_changed"
    if combo_name == CONTROL_COMBO:
        return "scoring_method_changed"
    return "model_and_scoring_method_changed"


def _result_row(
    *,
    strategy_name: str,
    mode: str,
    result,
    scoring_config,
    combo_name: str | None,
) -> dict[str, object]:
    monthly = result.monthly_result
    combo = _combo_metadata(combo_name)
    judge_models = str(combo["combo_judge_models"] or _judge_models_from_env())
    supervisor_model = str(combo["combo_supervisor_model"] or _supervisor_model_from_env())
    model_label = _model_label(scoring_config.provider, scoring_config.model)
    if strategy_name == "triple_supervisor" and mode == "llm":
        if not judge_models:
            judge_models = "; ".join([model_label, model_label, model_label])
        if not supervisor_model:
            supervisor_model = "rule:mode_if_available_else_median"
    row: dict[str, object] = {
        "run_id": uuid.uuid4().hex,
        "row_type": "data",
        "logged_at": datetime.now().isoformat(timespec="seconds"),
        "demo_dataset": CURRENT_DEMO_DATASET,
        "run_batch": CURRENT_RUN_BATCH,
        "prompt_version": PROMPT_VERSIONS.get(strategy_name, "unknown_prompt_version"),
        "experiment_family": _experiment_family(strategy_name),
        "experiment_group": _experiment_group(
            strategy_name=strategy_name,
            combo_name=combo_name,
        ),
        "experiment_variable": _experiment_variable(
            strategy_name=strategy_name,
            combo_name=combo_name,
        ),
        "strategy": strategy_name,
        "mode": mode,
        "experiment_combo": combo["experiment_combo"],
        "combo_description": combo["combo_description"],
        "provider": scoring_config.provider,
        "model": scoring_config.model,
        "model_label": model_label,
        "judge_models": judge_models,
        "supervisor_model": supervisor_model,
        "period_key": monthly.period_key,
        "previous_mbti": monthly.previous_estimated_mbti_type,
        "final_mbti": monthly.estimated_mbti_type,
        "changed_axes": ",".join(monthly.changed_axes),
        "changed_preferences": _changed_preferences(
            monthly.previous_estimated_mbti_type,
            monthly.estimated_mbti_type,
        ),
        "status": monthly.status,
    }

    for axis in AXIS_ORDER:
        axis_result = result.final_axis_results[axis]
        row[f"{axis}_previous_letter"] = axis_result.baseline_letter
        row[f"{axis}_letter"] = axis_result.selected_letter
        row[f"{axis}_previous_display_score"] = _previous_display_score(axis_result)
        row[f"{axis}_display_score"] = _display_score(axis_result)
        row[f"{axis}_display_score_delta"] = _axis_delta(axis_result)
        row[f"{axis}_previous_axis_avg"] = axis_result.previous_axis_avg
        row[f"{axis}_axis_avg"] = axis_result.axis_avg
        row[f"{axis}_axis_avg_delta"] = (
            None
            if axis_result.previous_axis_avg is None or axis_result.axis_avg is None
            else axis_result.axis_avg - axis_result.previous_axis_avg
        )
        row[f"{axis}_data_status"] = axis_result.data_status
        row[f"{axis}_scored_count"] = axis_result.scored_count

    return row


def _csv_fieldnames() -> list[str]:
    fields = [
        "run_id",
        "row_type",
        "logged_at",
        "demo_dataset",
        "run_batch",
        "prompt_version",
        "experiment_family",
        "experiment_group",
        "experiment_variable",
        "strategy",
        "mode",
        "experiment_combo",
        "combo_description",
        "provider",
        "model",
        "model_label",
        "judge_models",
        "supervisor_model",
        "period_key",
        "previous_mbti",
        "final_mbti",
        "changed_axes",
        "changed_preferences",
        "status",
    ]
    for axis in AXIS_ORDER:
        fields.extend(
            [
                f"{axis}_previous_letter",
                f"{axis}_letter",
                f"{axis}_previous_display_score",
                f"{axis}_display_score",
                f"{axis}_display_score_delta",
                f"{axis}_previous_axis_avg",
                f"{axis}_axis_avg",
                f"{axis}_axis_avg_delta",
                f"{axis}_data_status",
                f"{axis}_scored_count",
            ]
        )
    return fields


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    return float(stripped)


def _mode_and_rate(values: list[str]) -> tuple[str, float, int]:
    clean_values = [value for value in values if value]
    if not clean_values:
        return "", 0.0, 0
    counts = Counter(clean_values)
    mode, count = counts.most_common(1)[0]
    return mode, count / len(clean_values), len(counts)


def _std(values: list[float | None]) -> float:
    clean_values = [value for value in values if value is not None]
    if len(clean_values) <= 1:
        return 0.0
    return pstdev(clean_values)


def _build_analysis_row(*, strategy_name: str, rows: list[dict[str, object]]) -> dict[str, object]:
    data_rows = [row for row in rows if row.get("row_type", "data") != "analysis"]
    row: dict[str, object] = {field: "" for field in _csv_fieldnames()}
    row["run_id"] = "ANALYSIS"
    row["row_type"] = "analysis"
    row["logged_at"] = datetime.now().isoformat(timespec="seconds")
    row["strategy"] = strategy_name
    row["status"] = "analysis"

    if not data_rows:
        row["combo_description"] = "No experiment data rows yet."
        return row

    latest = data_rows[-1]
    row["demo_dataset"] = latest.get("demo_dataset", "")
    row["run_batch"] = latest.get("run_batch", "")
    row["prompt_version"] = latest.get("prompt_version", "")
    row["experiment_family"] = latest.get("experiment_family", "")
    row["experiment_group"] = "analysis"
    row["experiment_variable"] = "analysis"
    row["mode"] = "analysis"
    row["period_key"] = latest.get("period_key", "")

    final_mbti_mode, final_mbti_rate, final_mbti_unique_count = _mode_and_rate(
        [str(data_row.get("final_mbti", "")) for data_row in data_rows]
    )
    changed_mode, _, _ = _mode_and_rate(
        [str(data_row.get("changed_preferences", "")) for data_row in data_rows]
    )
    row["final_mbti"] = final_mbti_mode
    row["changed_preferences"] = changed_mode
    row["combo_description"] = (
        f"runs={len(data_rows)}; "
        f"final_mbti_mode={final_mbti_mode}; "
        f"final_mbti_rate={final_mbti_rate:.2f}; "
        f"final_mbti_unique={final_mbti_unique_count}"
    )

    for axis in AXIS_ORDER:
        letter_mode, letter_rate, letter_unique_count = _mode_and_rate(
            [str(data_row.get(f"{axis}_letter", "")) for data_row in data_rows]
        )
        display_std = _std(
            [_as_float(data_row.get(f"{axis}_display_score")) for data_row in data_rows]
        )
        axis_avg_std = _std(
            [_as_float(data_row.get(f"{axis}_axis_avg")) for data_row in data_rows]
        )
        row[f"{axis}_letter"] = letter_mode
        row[f"{axis}_display_score"] = f"std={display_std:.4f}"
        row[f"{axis}_axis_avg"] = f"std={axis_avg_std:.4f}"
        row[f"{axis}_data_status"] = (
            f"letter_rate={letter_rate:.2f}; unique={letter_unique_count}"
        )

    return row


def _append_row(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _csv_fieldnames()
    existing_rows: list[dict[str, object]] = []
    if path.exists() and path.stat().st_size > 0:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            existing_rows = [
                existing_row
                for existing_row in reader
                if existing_row.get("row_type", "data") != "analysis"
            ]
            existing_fieldnames = reader.fieldnames or []
            if "row_type" not in existing_fieldnames:
                for existing_row in existing_rows:
                    existing_row["row_type"] = "data"

    rows = existing_rows + [row]
    current_dataset = str(row.get("demo_dataset", ""))
    current_run_batch = str(row.get("run_batch", ""))
    current_prompt_version = str(row.get("prompt_version", ""))
    analysis_rows = [
        existing_row
        for existing_row in rows
        if str(existing_row.get("demo_dataset", "")) == current_dataset
        and str(existing_row.get("run_batch", "")) == current_run_batch
        and str(existing_row.get("prompt_version", "")) == current_prompt_version
    ]
    rows.append(_build_analysis_row(strategy_name=str(row["strategy"]), rows=analysis_rows))
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _strategy_results_path(strategy_name: str) -> Path:
    return STRATEGY_DIRS[strategy_name] / "results" / RESULT_FILE_NAME


def _default_scoring_client_for_strategy(
    *,
    strategy_name: str,
    use_persona_llm: bool,
    use_rubric_llm: bool,
    use_triple_supervisor_llm: bool,
):
    if strategy_name == "persona_direct" and use_persona_llm:
        return PersonaDirectLlmScoringClient()

    if strategy_name == "triple_supervisor" and use_triple_supervisor_llm:
        supervisor_dir = STRATEGY_DIRS["triple_supervisor"]
        supervisor_dir_text = str(supervisor_dir)
        if supervisor_dir_text not in sys.path:
            sys.path.insert(0, supervisor_dir_text)

        module = importlib.import_module("pipeline.response_scoring")
        return module.TripleSupervisorScoringClient()

    if strategy_name != "rubric_code":
        return None

    rubric_dir = STRATEGY_DIRS["rubric_code"]
    rubric_dir_text = str(rubric_dir)
    if rubric_dir_text not in sys.path:
        sys.path.insert(0, rubric_dir_text)

    module = importlib.import_module("pipeline.response_scoring")
    return module.RubricCodeScoringClient(use_llm=use_rubric_llm)


def _refresh_stability_outputs(strategy_names: tuple[str, ...]) -> None:
    summaries = []
    for name in strategy_names:
        summaries.extend(
            summarize_strategy(
                strategy_name=name,
                strategy_dir=STRATEGY_DIRS[name],
                result_file_name=RESULT_FILE_NAME,
                summary_file_name=SUMMARY_FILE_NAME,
                report_file_name=REPORT_FILE_NAME,
            )
        )
    write_dashboard(
        BASE_DIR / DASHBOARD_FILE_NAME,
        summaries,
        result_file_name=RESULT_FILE_NAME,
        report_file_name=REPORT_FILE_NAME,
    )


def run(
    *,
    strategy_name: str | None = None,
    use_persona_llm: bool = False,
    use_rubric_llm: bool = False,
    use_triple_supervisor_llm: bool = False,
    scoring_client_override=None,
    mode_override: str | None = None,
    combo_name: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    from demo_data import build_demo_monthly_question_batch
    from monthly_demo_payload import (
        DemoReportClient,
        build_demo_baseline_snapshot,
    )
    from mbti.services.monthly_pipeline import run_monthly_mbti_pipeline

    combo = EXPERIMENT_COMBOS.get(combo_name or "")
    selected_provider = provider or (str(combo["provider"]) if combo else None)
    selected_model = model or (str(combo["model"]) if combo else None)
    scoring_config = _build_scoring_config(
        provider=selected_provider,
        model=selected_model,
    )

    _, batch = build_demo_monthly_question_batch()
    baseline_snapshot = build_demo_baseline_snapshot(batch.user_id)
    strategies = build_strategies(
        use_persona_llm=use_persona_llm,
        use_rubric_llm=use_rubric_llm,
    )
    if strategy_name is not None:
        strategies = tuple(strategy for strategy in strategies if strategy.name == strategy_name)
        if not strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}")

    executed_strategy_names: list[str] = []
    for strategy in strategies:
        default_scoring_client = _default_scoring_client_for_strategy(
            strategy_name=strategy.name,
            use_persona_llm=use_persona_llm,
            use_rubric_llm=use_rubric_llm,
            use_triple_supervisor_llm=use_triple_supervisor_llm,
        )
        scoring_client = (
            scoring_client_override
            if scoring_client_override is not None and strategy.name == strategy_name
            else default_scoring_client or StrategyScoringClient(strategy)
        )
        result = run_monthly_mbti_pipeline(
            batch=batch,
            baseline_snapshot=baseline_snapshot,
            scoring_client=scoring_client,
            scoring_config=scoring_config,
            report_client=DemoReportClient(),
        )
        mode = mode_override or (
            "llm" if (
                (strategy.name == "persona_direct" and use_persona_llm)
                or (strategy.name == "rubric_code" and use_rubric_llm)
                or (strategy.name == "triple_supervisor" and use_triple_supervisor_llm)
            )
            else (
                "rubric_file_placeholder"
                if strategy.name == "rubric_code"
                else "placeholder"
            )
        )
        row = _result_row(
            strategy_name=strategy.name,
            mode=mode,
            result=result,
            scoring_config=scoring_config,
            combo_name=combo_name,
        )
        output_path = _strategy_results_path(strategy.name)
        _append_row(output_path, row)
        executed_strategy_names.append(strategy.name)
        print(f"wrote {output_path}")
        print(
            f"{strategy.name}: "
            f"{row['previous_mbti']} -> {row['final_mbti']} "
            f"({row['changed_preferences'] or 'no letter change'}), "
            f"model={row['model_label']}"
        )
    _refresh_stability_outputs(tuple(STRATEGY_DIRS))
    print(f"wrote {BASE_DIR / DASHBOARD_FILE_NAME}")


def main() -> None:
    args = parse_args()
    run(
        strategy_name=args.strategy,
        use_persona_llm=args.use_persona_llm,
        use_rubric_llm=args.use_rubric_llm,
        use_triple_supervisor_llm=args.use_triple_supervisor_llm,
        combo_name=args.combo,
        provider=args.provider,
        model=args.model,
    )


if __name__ == "__main__":
    main()
