from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = PROJECT_ROOT / "etl" / "datasets"
SOURCE_DIR = DATASET_ROOT / "\uc911\uac04 \uac00\uacf5 \ub370\uc774\ud130" / "huggingface_epinfomax_mbti_korean_dataset_csv"
LABEL_MAPPING_PATH = (
    DATASET_ROOT
    / "\uc6d0\ucc9c \ub370\uc774\ud130"
    / "huggingface_epinfomax_mbti_korean_dataset"
    / "label_mapping.json"
)
OUTPUT_DIR = DATASET_ROOT / "\uc2e4\uc0ac\uc6a9 \ub370\uc774\ud130" / "epinfomax_mbti_korean_4axis"

SOURCE_FILES = {
    "train": "huggingface_epinfomax_mbti_korean_dataset_train.csv",
    "validation": "huggingface_epinfomax_mbti_korean_dataset_validation.csv",
    "test": "huggingface_epinfomax_mbti_korean_dataset_test.csv",
}

OUTPUT_COLUMNS = ["text", "label", "mbti_type", "EI", "NS", "FT", "JP"]
AXIS_COLUMNS = ["EI", "NS", "FT", "JP"]

# Practical floor for four binary classifiers over text embeddings.
MIN_REQUIREMENTS = {
    "train": {"rows": 8000, "axis_min_class": 2000},
    "validation": {"rows": 1000, "axis_min_class": 250},
    "test": {"rows": 1000, "axis_min_class": 250},
}

EXPLICIT_TYPE_PATTERN = re.compile(
    r"(?i)(?:enfj|enfp|entj|entp|esfj|esfp|estj|estp|"
    r"infj|infp|intj|intp|isfj|isfp|istj|istp)"
)
GENERIC_MBTI_PATTERN = re.compile(
    r"(?i)(?:mbti|16personalities|16 personalities)|"
    r"(?:\uc5e0\ube44\ud2f0\uc544\uc774|\uc131\uaca9\s*\uc720\ud615)"
)
KOREAN_MBTI_ALIAS_PATTERN = re.compile(
    r"(?:"
    r"\uc5d4\ud504\uc81c|\uc5d4\ud504\ud53c|\uc5d4\ud2f0\uc81c|\uc5d4\ud301|"
    r"\uc5e3\ud504\uc81c|\uc5e3\ud504\ud53c|\uc5e3\ud2f0\uc81c|\uc5e3\ud301|"
    r"\uc778\ud504\uc81c|\uc778\ud504\ud53c|\uc778\ud2f0\uc81c|\uc778\ud301|"
    r"\uc787\ud504\uc81c|\uc787\ud504\ud53c|\uc787\ud2f0\uc81c|\uc787\ud301"
    r")"
)
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
ENGLISH_LETTER_PATTERN = re.compile(r"[A-Za-z]")
DIGIT_PATTERN = re.compile(r"[0-9]")
KOREAN_TEXT_PATTERN = re.compile(r"[\uac00-\ud7a3]")
KOREAN_DIGIT_PATTERN = re.compile(r"[\uac00-\ud7a30-9]")
NON_EMBEDDING_TEXT_PATTERN = re.compile(r"[^\uac00-\ud7a30-9\s?!~.\u314b\u314e\u315c\u3160]")
REPEATED_EMOTION_MARK_PATTERN = re.compile(r"([?!~.\u314b\u314e\u315c\u3160])\1{3,}")
SPACED_EMOTION_MARK_PATTERN = re.compile(r"([?!~.])\s+(?=[?!~.])")
SPACE_BEFORE_EMOTION_MARK_PATTERN = re.compile(r"\s+([?!~.])")
ORPHAN_PRONOUN_CONNECTIVE_PATTERN = re.compile(
    r"\b(\ub098\ub294|\uc800\ub294|\uc804|\ub098\ub3c4|\uc800\ub3c4)\s+"
    r"(\uc778\ub370\uc694?|\ub77c\uc11c|\ub77c|\uc774\ub77c\uc11c|\uc774\ub77c)\b"
)
WHITESPACE_PATTERN = re.compile(r"\s+")
MIN_CONTEXT_CHARS = 25
SPLIT_ORDER = ["train", "validation", "test"]


def load_label_mapping() -> dict[int, str]:
    mapping = json.loads(LABEL_MAPPING_PATH.read_text(encoding="utf-8"))
    return {int(label_id): mbti_type for label_id, mbti_type in mapping["id2label"].items()}


def mbti_to_axes(mbti_type: str) -> dict[str, str]:
    if len(mbti_type) != 4:
        raise ValueError(f"Invalid MBTI type: {mbti_type}")
    return {
        "EI": mbti_type[0],
        "NS": mbti_type[1],
        "FT": mbti_type[2],
        "JP": mbti_type[3],
    }


def normalize_whitespace(text: object) -> str:
    return WHITESPACE_PATTERN.sub(" ", str(text)).strip()


def sanitize_for_embedding(text: object) -> str:
    cleaned = normalize_whitespace(text)
    cleaned = URL_PATTERN.sub(" ", cleaned)
    cleaned = EXPLICIT_TYPE_PATTERN.sub(" ", cleaned)
    cleaned = GENERIC_MBTI_PATTERN.sub(" ", cleaned)
    cleaned = KOREAN_MBTI_ALIAS_PATTERN.sub(" ", cleaned)
    cleaned = ENGLISH_LETTER_PATTERN.sub(" ", cleaned)
    cleaned = NON_EMBEDDING_TEXT_PATTERN.sub(" ", cleaned)
    cleaned = ORPHAN_PRONOUN_CONNECTIVE_PATTERN.sub(r"\1 ", cleaned)
    cleaned = SPACED_EMOTION_MARK_PATTERN.sub(r"\1", cleaned)
    cleaned = SPACE_BEFORE_EMOTION_MARK_PATTERN.sub(r"\1", cleaned)
    cleaned = REPEATED_EMOTION_MARK_PATTERN.sub(lambda match: match.group(1) * 3, cleaned)
    return normalize_whitespace(cleaned)


def has_minimum_context(text: str) -> bool:
    context_chars = KOREAN_DIGIT_PATTERN.findall(text)
    return len(context_chars) >= MIN_CONTEXT_CHARS and bool(KOREAN_TEXT_PATTERN.search(text))


def add_labels(df: pd.DataFrame, id2label: dict[int, str]) -> pd.DataFrame:
    out = df.copy()
    out["mbti_type"] = out["label"].map(id2label)
    axes = out["mbti_type"].map(mbti_to_axes).apply(pd.Series)
    return pd.concat([out, axes], axis=1)[OUTPUT_COLUMNS]


def axis_min_counts(out: pd.DataFrame) -> dict[str, dict[str, int]]:
    return {
        axis: {str(k): int(v) for k, v in out[axis].value_counts().sort_index().items()}
        for axis in AXIS_COLUMNS
    }


def meets_minimum(out: pd.DataFrame, split: str) -> bool:
    requirement = MIN_REQUIREMENTS[split]
    if len(out) < requirement["rows"]:
        return False
    counts = axis_min_counts(out)
    return all(min(axis_counts.values()) >= requirement["axis_min_class"] for axis_counts in counts.values())


def validate_axis_labels(out: pd.DataFrame) -> None:
    expected_axes = out["mbti_type"].map(mbti_to_axes).apply(pd.Series)
    for axis in AXIS_COLUMNS:
        mismatch_count = int((out[axis] != expected_axes[axis]).sum())
        if mismatch_count:
            raise ValueError(f"{axis} label mismatch from mbti_type: {mismatch_count}")


def raw_flags(texts: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "url_like": texts.map(lambda text: bool(URL_PATTERN.search(text))),
            "english_letter": texts.map(lambda text: bool(ENGLISH_LETTER_PATTERN.search(text))),
            "digit": texts.map(lambda text: bool(DIGIT_PATTERN.search(text))),
            "explicit_mbti_type": texts.map(lambda text: bool(EXPLICIT_TYPE_PATTERN.search(text))),
            "generic_mbti_term": texts.map(lambda text: bool(GENERIC_MBTI_PATTERN.search(text))),
            "korean_mbti_alias": texts.map(lambda text: bool(KOREAN_MBTI_ALIAS_PATTERN.search(text))),
            "symbol_or_punctuation": texts.map(lambda text: bool(NON_EMBEDDING_TEXT_PATTERN.search(text))),
        },
        index=texts.index,
    )


def convert_split(split: str, source_file: str, id2label: dict[int, str]) -> tuple[pd.DataFrame, dict[str, object]]:
    source_path = SOURCE_DIR / source_file
    df = pd.read_csv(source_path, encoding="utf-8-sig")
    if list(df.columns) != ["text", "label"]:
        raise ValueError(f"Unexpected columns in {source_path}: {list(df.columns)}")

    df["label"] = df["label"].astype(int)
    unknown_labels = sorted(set(df["label"]) - set(id2label))
    if unknown_labels:
        raise ValueError(f"Unknown labels in {source_path}: {unknown_labels}")

    original_rows = len(df)
    original_texts = df["text"].fillna("").astype(str).map(normalize_whitespace)
    flags = raw_flags(original_texts)

    df["text"] = original_texts.map(sanitize_for_embedding)
    context_mask = df["text"].map(has_minimum_context)
    no_context_rows = int((~context_mask).sum())
    df = df.loc[context_mask].copy()

    duplicate_rows_after_sanitize = int(df.duplicated(subset=["text"], keep=False).sum())
    out = add_labels(df, id2label)
    validate_axis_labels(out)

    direct_noise_rows = flags[
        [
            "english_letter",
            "explicit_mbti_type",
            "generic_mbti_term",
            "korean_mbti_alias",
            "digit",
            "symbol_or_punctuation",
        ]
    ].any(axis=1)

    return out, {
        "split": split,
        "source_file": str(source_path.relative_to(PROJECT_ROOT)),
        "output_file": str(
            (
                OUTPUT_DIR / f"huggingface_epinfomax_mbti_korean_4axis_{split}.csv"
            ).relative_to(PROJECT_ROOT)
        ),
        "minimum_requirement": MIN_REQUIREMENTS[split],
        "minimum_requirement_met_before_dedup": meets_minimum(out, split),
        "policy_applied": "sanitize_text_min_length_global_deduplicate",
        "original_rows": int(original_rows),
        "rows_after_sanitization": int(len(out)),
        "removed_rows_after_sanitization_due_to_lost_context": no_context_rows,
        "rows_restored_by_text_sanitization": int(direct_noise_rows.sum() - no_context_rows),
        "flag_counts_before_sanitization": {name: int(flags[name].sum()) for name in flags.columns},
        "duplicate_text_rows_after_sanitization": duplicate_rows_after_sanitize,
        "columns": OUTPUT_COLUMNS,
        "axis_counts_after_sanitization": axis_min_counts(out),
        "mbti_type_counts_after_sanitization": {
            str(k): int(v) for k, v in out["mbti_type"].value_counts().sort_index().items()
        },
    }


def remove_duplicate_texts(
    split_frames: dict[str, pd.DataFrame],
    split_summaries: dict[str, dict[str, object]],
) -> dict[str, pd.DataFrame]:
    seen_texts: set[str] = set()
    deduped_frames: dict[str, pd.DataFrame] = {}

    for split in SPLIT_ORDER:
        out = split_frames[split].copy()
        duplicate_mask = out["text"].isin(seen_texts) | out.duplicated(subset=["text"], keep="first")
        deduped = out.loc[~duplicate_mask].copy()
        seen_texts.update(deduped["text"].tolist())

        split_summaries[split]["removed_duplicate_rows_global"] = int(duplicate_mask.sum())
        split_summaries[split]["rows"] = int(len(deduped))
        split_summaries[split]["minimum_requirement_met"] = meets_minimum(deduped, split)
        split_summaries[split]["axis_counts"] = axis_min_counts(deduped)
        split_summaries[split]["mbti_type_counts"] = {
            str(k): int(v) for k, v in deduped["mbti_type"].value_counts().sort_index().items()
        }

        if not split_summaries[split]["minimum_requirement_met"]:
            raise ValueError(
                f"{split} does not meet minimum requirements after deduplication: "
                f"rows={len(deduped)}, axis_counts={axis_min_counts(deduped)}"
            )

        deduped_frames[split] = deduped

    return deduped_frames


def save_split(split: str, out: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"huggingface_epinfomax_mbti_korean_4axis_{split}.csv"
    out.to_csv(output_path, index=False, encoding="utf-8-sig")


def main() -> None:
    id2label = load_label_mapping()
    converted: dict[str, pd.DataFrame] = {}
    summaries: dict[str, dict[str, object]] = {}

    for split in SPLIT_ORDER:
        out, summary = convert_split(split, SOURCE_FILES[split], id2label)
        converted[split] = out
        summaries[split] = summary

    deduped = remove_duplicate_texts(converted, summaries)
    for split, out in deduped.items():
        save_split(split, out)

    results = [summaries[split] for split in SPLIT_ORDER]
    summary = {
        "source": "https://huggingface.co/datasets/epinfomax/mbti-korean-dataset",
        "label_mapping_source": "https://huggingface.co/datasets/epinfomax/mbti-korean-dataset/blob/main/train_hf_skills.py",
        "purpose": "Create embedding-ready Korean text while preserving usable rows, then add mbti_type and EI/NS/FT/JP labels.",
        "minimum_row_assumption": {
            "basis": "Four independent binary classifiers trained on text embeddings. Minimum is a practical baseline threshold, not an optimal-data claim.",
            "requirements": MIN_REQUIREMENTS,
        },
        "preprocessing": {
            "keeps_original_split": True,
            "row_policy": "Do not remove rows for English letters, MBTI mentions, digits, or symbols. Remove those characters inside text and keep rows when Korean context remains.",
            "text_sanitization": [
                "Trim text and collapse whitespace.",
                "Remove URL-like spans.",
                "Remove direct 16-type MBTI names even when attached to Korean particles or English letters.",
                "Remove generic MBTI leakage terms.",
                "Remove Korean MBTI aliases such as 엔프피, 인프피, 잇팁, and 엣팁.",
                "Remove all English letters.",
                "Keep digits because age, duration, count, order, and time expressions can preserve context.",
                "Keep conservative emotion markers: ?, !, ~, ., ㅋ, ㅎ, ㅜ, ㅠ.",
                "Collapse repeated emotion markers to at most 3 characters.",
                "Remove other symbols and punctuation, keeping Korean characters, digits, selected emotion markers, and spaces.",
                f"Drop rows whose sanitized text has fewer than {MIN_CONTEXT_CHARS} Korean/digit context characters.",
                "Remove duplicate sanitized texts within each split.",
                "Remove duplicate sanitized texts across splits by train -> validation -> test priority to reduce leakage.",
            ],
        },
        "id2label": {str(k): v for k, v in id2label.items()},
        "splits": results,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
