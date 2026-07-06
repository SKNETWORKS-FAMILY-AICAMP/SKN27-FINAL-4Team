from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import json
import os
import re
from statistics import median
from typing import Any, Mapping, Sequence

from mbti.services.persona import build_axis_scoring_system_prompt


VALID_CODING_STATUSES = {"coded", "insufficient_context", "failed"}
VALID_SCORES = (-1.0, -0.5, 0.0, 0.5, 1.0)
AXIS_DIRECTION_LABELS = {
    "IE": ("I", "E"),
    "SN": ("N", "S"),
    "TF": ("F", "T"),
    "JP": ("P", "J"),
}

    
@dataclass(frozen=True)
class JudgeConfig:
    label: str
    provider: str
    model: str
    temperature: float
    max_output_tokens: int


def build_axis_scoring_input(*, axis: str, responses: Sequence[Any]) -> str:
    negative, positive = AXIS_DIRECTION_LABELS[axis]
    payload = {
        "axis": axis,
        "score_scale": {
            "-1.0": f"strong {negative}",
            "-0.5": f"slightly {negative}",
            "0.0": "neutral or mixed",
            "0.5": f"slightly {positive}",
            "1.0": f"strong {positive}",
            "null": "not enough evidence",
        },
        "responses": [
            {
                "response_id": response.id,
                "question": response.question_text,
                "answer": response.answer_text,
            }
            for response in responses
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


class TripleSupervisorScoringClient:
    """Run three persona-prompt LLM judges and merge them with deterministic rules."""

    def score_axis_responses(self, *, axis, responses, config):
        judge_configs = _resolve_judge_configs(config)
        judge_payloads = [
            _score_with_judge(
                judge_config=judge_config,
                axis=axis,
                responses=responses,
            )
            for judge_config in judge_configs
        ]
        return supervise_scoring_payloads(
            axis=axis,
            responses=responses,
            judge_payloads=judge_payloads,
            judge_labels=[judge_config.label for judge_config in judge_configs],
        )


def supervise_scoring_payloads(
    *,
    axis: str,
    responses: Sequence[Any],
    judge_payloads: Sequence[Mapping[str, Any]],
    judge_labels: Sequence[str] = ("judge_1", "judge_2", "judge_3"),
) -> dict[str, Any]:
    rows_by_response_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    valid_response_ids = {int(response.id) for response in responses}

    for judge_index, payload in enumerate(judge_payloads):
        label = judge_labels[judge_index] if judge_index < len(judge_labels) else f"judge_{judge_index + 1}"
        for row in payload.get("scores", []):
            try:
                response_id = int(row.get("response_id"))
            except (TypeError, ValueError):
                continue
            if response_id not in valid_response_ids:
                continue
            normalized = _normalize_score_row(row)
            normalized["judge_label"] = label
            rows_by_response_id[response_id].append(normalized)

    supervised_scores = []
    for response in responses:
        response_rows = rows_by_response_id.get(int(response.id), [])
        supervised_scores.append(
            _supervise_response_scores(
                response_id=int(response.id),
                rows=response_rows,
            )
        )

    return {
        "scores": supervised_scores,
        "supervisor": {
            "rule": "mode_if_available_else_median",
            "coded_quorum": 2,
            "axis": axis,
        },
    }


def _supervise_response_scores(*, response_id: int, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    coded_rows = [
        row
        for row in rows
        if row.get("coding_status") == "coded" and row.get("score") is not None
    ]
    coded_scores = [float(row["score"]) for row in coded_rows]

    if len(coded_scores) >= 2:
        score_counts = Counter(coded_scores)
        score, count = score_counts.most_common(1)[0]
        if count >= 2:
            decision = "mode"
            final_score = score
        else:
            decision = "median"
            final_score = float(median(coded_scores))
        return {
            "response_id": response_id,
            "score": final_score,
            "coding_status": "coded",
            "reason": _build_supervisor_reason(decision=decision, rows=rows),
        }

    status_counts = Counter(str(row.get("coding_status") or "failed") for row in rows)
    if status_counts.get("failed", 0) == len(rows):
        final_status = "failed"
    else:
        final_status = "insufficient_context"
    return {
        "response_id": response_id,
        "score": None,
        "coding_status": final_status,
        "reason": _build_supervisor_reason(decision=f"{final_status}_no_coded_quorum", rows=rows),
    }


def _normalize_score_row(row: Mapping[str, Any]) -> dict[str, Any]:
    coding_status = str(row.get("coding_status") or "failed")
    if coding_status not in VALID_CODING_STATUSES:
        coding_status = "failed"

    score = row.get("score")
    if coding_status != "coded":
        score = None
    else:
        try:
            score = _nearest_valid_score(float(score))
        except (TypeError, ValueError):
            score = None
            coding_status = "failed"

    return {
        "response_id": row.get("response_id"),
        "score": score,
        "coding_status": coding_status,
        "reason": str(row.get("reason") or ""),
    }


def _nearest_valid_score(value: float) -> float:
    return min(VALID_SCORES, key=lambda score: abs(score - value))


def _build_supervisor_reason(*, decision: str, rows: Sequence[Mapping[str, Any]]) -> str:
    parts = [f"supervisor_decision={decision}"]
    for index, row in enumerate(rows, start=1):
        label = row.get("judge_label") or f"judge_{index}"
        parts.append(
            f"{label}: status={row.get('coding_status')}, score={row.get('score')}, reason={row.get('reason')}"
        )
    return " | ".join(parts)


def _resolve_judge_configs(config: Any) -> tuple[JudgeConfig, JudgeConfig, JudgeConfig]:
    default_provider = str(getattr(config, "provider", "openai") or "openai")
    default_model = str(getattr(config, "model", "gpt-5.4-mini") or "gpt-5.4-mini")
    default_temperature = float(getattr(config, "temperature", 0.0) or 0.0)
    default_max_tokens = int(getattr(config, "max_output_tokens", 1200) or 1200)

    configs = []
    for index in range(1, 4):
        provider = os.getenv(f"MBTI_JUDGE_{index}_PROVIDER") or default_provider
        model = os.getenv(f"MBTI_JUDGE_{index}_MODEL") or default_model
        label = os.getenv(f"MBTI_JUDGE_{index}_LABEL") or f"judge_{index}:{provider}:{model}"
        configs.append(
            JudgeConfig(
                label=label,
                provider=provider,
                model=model,
                temperature=default_temperature,
                max_output_tokens=default_max_tokens,
            )
        )
    return tuple(configs)  # type: ignore[return-value]


def _score_with_judge(*, judge_config: JudgeConfig, axis: str, responses: Sequence[Any]) -> Mapping[str, Any]:
    try:
        content = _openai_compatible_chat_content(
            provider=judge_config.provider,
            model=judge_config.model,
            system_prompt=build_axis_scoring_system_prompt(),
            user_prompt=build_axis_scoring_input(axis=axis, responses=responses),
            temperature=judge_config.temperature,
            max_tokens=judge_config.max_output_tokens,
        )
        return _extract_json_object(str(content))
    except Exception as exc:
        return _build_failed_scoring_payload(
            responses=responses,
            reason=f"{judge_config.label} failed: {exc}",
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
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
    except ModuleNotFoundError as exc:
        missing = exc.name or "langchain dependency"
        raise ModuleNotFoundError(
            f"{missing} is required for triple_supervisor experiments. "
            "Install app/backend/requirements.txt in the Python environment "
            "used to run this script."
        ) from exc

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

    llm_kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_key:
        llm_kwargs["api_key"] = api_key
    if base_url:
        llm_kwargs["base_url"] = base_url

    message = ChatOpenAI(**llm_kwargs).invoke(
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


def _json_loads_lenient(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        escaped_invalid_backslashes = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", text)
        if escaped_invalid_backslashes == text:
            raise
        return json.loads(escaped_invalid_backslashes)


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        loaded = _json_loads_lenient(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}") + 1
        if start < 0 or end <= start:
            raise
        loaded = _json_loads_lenient(stripped[start:end])

    if not isinstance(loaded, dict):
        raise ValueError("LLM output must be a JSON object.")
    return loaded


def _build_failed_scoring_payload(*, responses: Sequence[Any], reason: str) -> dict[str, Any]:
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
