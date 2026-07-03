from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from statistics import pstdev
from typing import Iterable


AXIS_ORDER = ("IE", "SN", "TF", "JP")


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return [
            row
            for row in csv.DictReader(file)
            if row.get("row_type", "data") != "analysis"
        ]


def _as_float(value: str | None) -> float | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return float(stripped)


def _mode_and_rate(values: Iterable[str]) -> tuple[str, float, int]:
    items = [value for value in values if value]
    if not items:
        return "", 0.0, 0
    counts = Counter(items)
    mode, mode_count = counts.most_common(1)[0]
    return mode, mode_count / len(items), len(counts)


def _std(values: Iterable[float | None]) -> float:
    clean_values = [value for value in values if value is not None]
    if len(clean_values) <= 1:
        return 0.0
    return pstdev(clean_values)


def _stability_label(*, mbti_unique_count: int, mbti_rate: float, max_axis_avg_std: float) -> str:
    if mbti_unique_count == 1 and mbti_rate == 1.0 and max_axis_avg_std <= 0.05:
        return "안정"
    if mbti_unique_count <= 2 and mbti_rate >= 0.8 and max_axis_avg_std <= 0.15:
        return "주의"
    return "불안정"


def _group_key(row: dict[str, str]) -> str:
    demo_dataset = row.get("demo_dataset") or "legacy_demo_dataset"
    run_batch = row.get("run_batch") or "legacy_run_batch"
    prompt_version = row.get("prompt_version") or "legacy_prompt_version"
    mode = row.get("mode") or "unknown"
    combo = row.get("experiment_combo") or "custom"
    model_label = row.get("model_label") or ""
    judge_models = row.get("judge_models") or ""
    supervisor_model = row.get("supervisor_model") or ""
    parts = [demo_dataset, run_batch, prompt_version, mode, combo]
    if model_label:
        parts.append(model_label)
    if judge_models:
        parts.append(f"judges={judge_models}")
    if supervisor_model:
        parts.append(f"supervisor={supervisor_model}")
    return " / ".join(parts)


def _group_rows_by_mode(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(_group_key(row), []).append(row)
    return grouped


def summarize_rows(
    *,
    strategy_name: str,
    mode: str,
    rows: list[dict[str, str]],
) -> dict[str, object]:
    if not rows:
        return {
            "strategy": strategy_name,
            "mode": mode,
            "demo_dataset": "",
            "run_batch": "",
            "prompt_version": "",
            "run_count": 0,
            "stability_label": "데이터없음",
            "final_mbti_mode": "",
            "final_mbti_stability_rate": 0.0,
            "final_mbti_unique_count": 0,
            "changed_preferences_mode": "",
            "max_axis_avg_std": 0.0,
            "max_display_score_std": 0.0,
        }

    final_mbti_mode, final_mbti_rate, final_mbti_unique_count = _mode_and_rate(
        row.get("final_mbti", "") for row in rows
    )
    changed_mode, _, _ = _mode_and_rate(row.get("changed_preferences", "") for row in rows)

    summary: dict[str, object] = {
        "strategy": strategy_name,
        "mode": mode,
        "demo_dataset": rows[-1].get("demo_dataset", "") or "legacy_demo_dataset",
        "run_batch": rows[-1].get("run_batch", "") or "legacy_run_batch",
        "prompt_version": rows[-1].get("prompt_version", "") or "legacy_prompt_version",
        "experiment_family": rows[-1].get("experiment_family", ""),
        "experiment_group": rows[-1].get("experiment_group", ""),
        "experiment_variable": rows[-1].get("experiment_variable", ""),
        "experiment_combo": rows[-1].get("experiment_combo", ""),
        "model_label": rows[-1].get("model_label", ""),
        "judge_models": rows[-1].get("judge_models", ""),
        "supervisor_model": rows[-1].get("supervisor_model", ""),
        "run_count": len(rows),
        "final_mbti_mode": final_mbti_mode,
        "final_mbti_stability_rate": final_mbti_rate,
        "final_mbti_unique_count": final_mbti_unique_count,
        "changed_preferences_mode": changed_mode,
    }

    axis_avg_stds: list[float] = []
    display_score_stds: list[float] = []
    for axis in AXIS_ORDER:
        letter_mode, letter_rate, letter_unique_count = _mode_and_rate(
            row.get(f"{axis}_letter", "") for row in rows
        )
        display_score_std = _std(
            _as_float(row.get(f"{axis}_display_score")) for row in rows
        )
        axis_avg_std = _std(
            _as_float(row.get(f"{axis}_axis_avg")) for row in rows
        )
        axis_avg_stds.append(axis_avg_std)
        display_score_stds.append(display_score_std)

        summary[f"{axis}_letter_mode"] = letter_mode
        summary[f"{axis}_letter_stability_rate"] = letter_rate
        summary[f"{axis}_letter_unique_count"] = letter_unique_count
        summary[f"{axis}_display_score_std"] = display_score_std
        summary[f"{axis}_axis_avg_std"] = axis_avg_std

    summary["max_axis_avg_std"] = max(axis_avg_stds) if axis_avg_stds else 0.0
    summary["max_display_score_std"] = max(display_score_stds) if display_score_stds else 0.0
    summary["stability_label"] = _stability_label(
        mbti_unique_count=final_mbti_unique_count,
        mbti_rate=final_mbti_rate,
        max_axis_avg_std=float(summary["max_axis_avg_std"]),
    )
    return summary


def _summary_fieldnames() -> list[str]:
    fields = [
        "strategy",
        "mode",
        "demo_dataset",
        "run_batch",
        "prompt_version",
        "experiment_family",
        "experiment_group",
        "experiment_variable",
        "experiment_combo",
        "model_label",
        "judge_models",
        "supervisor_model",
        "run_count",
        "stability_label",
        "final_mbti_mode",
        "final_mbti_stability_rate",
        "final_mbti_unique_count",
        "changed_preferences_mode",
        "max_axis_avg_std",
        "max_display_score_std",
    ]
    for axis in AXIS_ORDER:
        fields.extend(
            [
                f"{axis}_letter_mode",
                f"{axis}_letter_stability_rate",
                f"{axis}_letter_unique_count",
                f"{axis}_display_score_std",
                f"{axis}_axis_avg_std",
            ]
        )
    return fields


def write_summary_csv(path: Path, summaries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=_summary_fieldnames(), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(summaries)


def _format_rate(value: object) -> str:
    return f"{float(value) * 100:.1f}%"


def _format_float(value: object) -> str:
    return f"{float(value):.4f}"


def _axis_avg_std_judgement(value: object) -> str:
    std = float(value)
    if std <= 0.05:
        return "낮음(안정)"
    if std <= 0.15:
        return "보통(주의)"
    return "높음(불안정)"


def _display_score_std_judgement(value: object) -> str:
    std = float(value)
    if std <= 3.0:
        return "낮음(안정)"
    if std <= 8.0:
        return "보통(주의)"
    return "높음(불안정)"


def write_strategy_report(path: Path, summaries: list[dict[str, object]]) -> None:
    if not summaries:
        path.write_text("# Stability Report\n\nNo runs yet.\n", encoding="utf-8")
        return

    lines = [
        f"# {summaries[0]['strategy']} Stability Report",
        "",
        "## 모드별 요약",
        "",
        "| 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in summaries:
        lines.append(
            "| "
            f"{summary['mode']} | "
            f"{summary['stability_label']} | "
            f"{summary['run_count']} | "
            f"{summary['final_mbti_mode']} | "
            f"{_format_rate(summary['final_mbti_stability_rate'])} | "
            f"{summary['final_mbti_unique_count']} | "
            f"{_format_float(summary['max_axis_avg_std'])} | "
            f"{_format_float(summary['max_display_score_std'])} | "
            f"{summary['changed_preferences_mode'] or '변화 없음'} |"
        )

    lines.extend(["", "## 축별 안정성", ""])
    for summary in summaries:
        lines.extend(
            [
                f"### {summary['mode']}",
                "",
                "| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for axis in AXIS_ORDER:
            lines.append(
                "| "
                f"{axis} | "
                f"{summary.get(f'{axis}_letter_mode', '')} | "
                f"{_format_rate(summary.get(f'{axis}_letter_stability_rate', 0.0))} | "
                f"{summary.get(f'{axis}_letter_unique_count', 0)} | "
                f"{_format_float(summary.get(f'{axis}_display_score_std', 0.0))} | "
                f"{_format_float(summary.get(f'{axis}_axis_avg_std', 0.0))} |"
            )
        lines.append("")
        lines.extend(
            [
                "#### 표준편차 판정",
                "",
                f"- max axis_avg 표준편차: {_format_float(summary['max_axis_avg_std'])} → {_axis_avg_std_judgement(summary['max_axis_avg_std'])}",
                f"- max 표시점수 표준편차: {_format_float(summary['max_display_score_std'])} → {_display_score_std_judgement(summary['max_display_score_std'])}",
                "- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.",
                "",
                "| 축 | axis_avg 판정 | 표시점수 판정 |",
                "| --- | --- | --- |",
            ]
        )
        for axis in AXIS_ORDER:
            lines.append(
                "| "
                f"{axis} | "
                f"{_axis_avg_std_judgement(summary.get(f'{axis}_axis_avg_std', 0.0))} | "
                f"{_display_score_std_judgement(summary.get(f'{axis}_display_score_std', 0.0))} |"
            )
        lines.append("")

    lines.extend(
        [
            "## 판정 기준",
            "",
            "| 판정 | 기준 |",
            "| --- | --- |",
            "| 안정 | 최종 MBTI가 1종이고 최대 axis_avg 표준편차가 0.05 이하 |",
            "| 주의 | 최종 MBTI가 2종 이하, 최빈 MBTI 비율 80% 이상, 최대 axis_avg 표준편차 0.15 이하 |",
            "| 불안정 | 위 기준을 벗어남 |",
        ]
    )
    lines.extend(
        [
            "",
            "## 표준편차 해석 기준",
            "",
            "| 지표 | 낮음(안정) | 보통(주의) | 높음(불안정) |",
            "| --- | --- | --- | --- |",
            "| axis_avg 표준편차 | 0.0500 이하 | 0.1500 이하 | 0.1500 초과 |",
            "| 표시점수 표준편차 | 3.0000 이하 | 8.0000 이하 | 8.0000 초과 |",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_strategy(*, strategy_name: str, strategy_dir: Path) -> list[dict[str, object]]:
    result_path = strategy_dir / "results" / "mbti_score_changes.csv"
    summary_path = strategy_dir / "results" / "stability_summary.csv"
    report_path = strategy_dir / "results" / "STABILITY_REPORT.md"
    rows = _read_rows(result_path)
    grouped = _group_rows_by_mode(rows)
    summaries = [
        summarize_rows(strategy_name=strategy_name, mode=mode, rows=mode_rows)
        for mode, mode_rows in sorted(grouped.items())
    ]
    if not summaries:
        summaries = [summarize_rows(strategy_name=strategy_name, mode="no_data", rows=[])]
    write_summary_csv(summary_path, summaries)
    write_strategy_report(report_path, summaries)
    return summaries


def write_dashboard(path: Path, summaries: Iterable[dict[str, object]]) -> None:
    rows = list(summaries)
    lines = [
        "# MBTI Scoring Stability Dashboard",
        "",
        "같은 backend 월간 데모 데이터에서 방안별 최종 MBTI와 축별 점수 흔들림을 비교한다.",
        "",
        "서로 다른 실행 모드가 섞이면 안정성이 왜곡될 수 있으므로 `strategy + mode` 단위로 분리해 표시한다.",
        "",
        "| 방식 | 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in rows:
        lines.append(
            "| "
            f"{summary['strategy']} | "
            f"{summary['mode']} | "
            f"{summary['stability_label']} | "
            f"{summary['run_count']} | "
            f"{summary['final_mbti_mode']} | "
            f"{_format_rate(summary['final_mbti_stability_rate'])} | "
            f"{summary['final_mbti_unique_count']} | "
            f"{_format_float(summary['max_axis_avg_std'])} | "
            f"{_format_float(summary['max_display_score_std'])} | "
            f"{summary['changed_preferences_mode'] or '변화 없음'} |"
        )
    lines.extend(
        [
            "",
            "표준편차 판정: axis_avg는 0.05 이하 안정, 0.15 이하 주의, 초과 불안정으로 본다. 표시점수는 3점 이하 안정, 8점 이하 주의, 초과 불안정으로 본다.",
            "",
            "각 방안의 상세 축별 안정성은 해당 폴더의 `results/STABILITY_REPORT.md`에서 확인한다.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
