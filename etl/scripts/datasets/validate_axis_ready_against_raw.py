from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = PROJECT_ROOT / "etl" / "datasets" / "personality_training"
AXIS_DIR = DATA_ROOT / "axis_ready"
REPORT_DIR = DATA_ROOT / "metadata"
BUILD_SCRIPT = PROJECT_ROOT / "etl" / "scripts" / "datasets" / "build_mbti_axis_ready_dataset.py"
MODEL_COLUMNS = ["text", "EI", "NS", "FT", "JP"]


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_mbti_axis_ready_dataset", BUILD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {BUILD_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_model_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df[MODEL_COLUMNS].drop_duplicates(subset=MODEL_COLUMNS).sort_values(MODEL_COLUMNS).reset_index(drop=True)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    builder = load_builder_module()

    expected = pd.concat(
        [builder.build_datasnaek(), builder.build_mbtibench()],
        ignore_index=True,
    )
    expected = normalize_model_frame(expected)

    actual_path = AXIS_DIR / "all_axis_ready.csv"
    actual = normalize_model_frame(pd.read_csv(actual_path))

    if len(expected) == len(actual):
        merged = expected.merge(actual, on=MODEL_COLUMNS, how="outer", indicator=True)
        missing_from_actual = int((merged["_merge"] == "left_only").sum())
        extra_in_actual = int((merged["_merge"] == "right_only").sum())
    else:
        merged = expected.merge(actual, on=MODEL_COLUMNS, how="outer", indicator=True)
        missing_from_actual = int((merged["_merge"] == "left_only").sum())
        extra_in_actual = int((merged["_merge"] == "right_only").sum())

    incomplete_but_raw_same = int((~actual["text"].str.endswith((".", "?", "!", "\"", "'", ")"), na=False)).sum())
    summary = {
        "axis_ready_file": str(actual_path),
        "expected_rows_from_raw_pipeline": int(len(expected)),
        "actual_rows": int(len(actual)),
        "missing_from_actual": missing_from_actual,
        "extra_in_actual": extra_in_actual,
        "possible_truncation_count": 0 if missing_from_actual == 0 and extra_in_actual == 0 else None,
        "incomplete_looking_rows": incomplete_but_raw_same,
        "conclusion": (
            "Current all_axis_ready.csv exactly matches rows regenerated from raw sources with the build pipeline."
            if missing_from_actual == 0 and extra_in_actual == 0
            else "Current all_axis_ready.csv differs from rows regenerated from raw sources."
        ),
    }
    (REPORT_DIR / "axis_ready_raw_comparison_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
