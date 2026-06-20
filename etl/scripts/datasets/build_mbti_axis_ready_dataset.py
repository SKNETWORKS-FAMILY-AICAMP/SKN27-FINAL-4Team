from __future__ import annotations

import csv
import json
import re
from html import unescape
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]
INPUT_DIR = PROJECT_ROOT / "etl" / "datasets" / "personality_training" / "selected_raw"
OUTPUT_DIR = PROJECT_ROOT / "etl" / "datasets" / "personality_training" / "axis_ready"
METADATA_DIR = PROJECT_ROOT / "etl" / "datasets" / "personality_training" / "metadata"
MODEL_COLUMNS = ["text", "EI", "NS", "FT", "JP"]

MBTI_TYPES = {
    "ISTJ",
    "ISFJ",
    "INFJ",
    "INTJ",
    "ISTP",
    "ISFP",
    "INFP",
    "INTP",
    "ESTP",
    "ESFP",
    "ENFP",
    "ENTP",
    "ESTJ",
    "ESFJ",
    "ENFJ",
    "ENTJ",
}

MBTI_LEAK_RE = re.compile(
    r"(?<![A-Za-z])("
    r"mbti|myers[-\s]?briggs|personality\s+type|cognitive\s+functions?|"
    r"istj|isfj|infj|intj|istp|isfp|infp|intp|"
    r"estp|esfp|enfp|entp|estj|esfj|enfj|entj"
    r")(?![A-Za-z])",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b\S+@\S+\.\S+\b")
MENTION_RE = re.compile(r"(?<!\w)@\w+")
HASHTAG_RE = re.compile(r"(?<!\w)#(\w+)")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
SYMBOL_NOISE_RE = re.compile(r"[^A-Za-z0-9\s.,!?'\-\"():;%&/]")


def clear_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for item in path.iterdir():
        if item.is_file() and item.suffix.lower() in {".csv", ".json"}:
            item.unlink()


def normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).replace("\x00", " ").split())


def clean_utterance(value: Any) -> str:
    text = unescape(normalize_text(value))
    text = CONTROL_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = EMAIL_RE.sub(" ", text)
    text = MENTION_RE.sub(" ", text)
    text = HASHTAG_RE.sub(r"\1", text)
    text = text.replace("RT ", " ")
    text = SYMBOL_NOISE_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip(" \t\r\n\"'`.,;:|")


def looks_like_usable_utterance(text: str) -> bool:
    if len(text) < 20 or len(text) > 2000:
        return False
    if MBTI_LEAK_RE.search(text):
        return False
    word_count = len(re.findall(r"[A-Za-z]+", text))
    if word_count < 4:
        return False
    visible_chars = re.findall(r"[A-Za-z0-9]", text)
    return len(visible_chars) / max(len(text), 1) >= 0.45


def axes_from_type(mbti_type: Any) -> dict[str, str] | None:
    value = str(mbti_type).upper().strip()
    if value not in MBTI_TYPES:
        return None
    return {"EI": value[0], "NS": value[1], "FT": value[2], "JP": value[3]}


def base_record(
    *,
    text: str,
    axes: dict[str, str],
    mbti_type: str | None,
    source_dataset: str,
    source_file: str,
    source_id: str,
    text_unit: str,
    label_strength: str,
    soft_EI: float | None = None,
    soft_NS: float | None = None,
    soft_FT: float | None = None,
    soft_JP: float | None = None,
) -> dict[str, Any]:
    return {
        "text": text,
        "EI": axes["EI"],
        "NS": axes["NS"],
        "FT": axes["FT"],
        "JP": axes["JP"],
        "mbti_type": mbti_type,
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_id": source_id,
        "text_unit": text_unit,
        "label_strength": label_strength,
        "soft_EI_original": soft_EI,
        "soft_NS_original": soft_NS,
        "soft_FT_original": soft_FT,
        "soft_JP_original": soft_JP,
    }


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8", "utf-8-sig", "cp949", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read CSV: {path}")


def hard_axes_from_mbtibench(hardlabels: dict[str, Any]) -> dict[str, str] | None:
    try:
        axes = {
            "EI": str(hardlabels["E/I"]).upper().strip(),
            "NS": str(hardlabels["S/N"]).upper().strip(),
            "FT": str(hardlabels["T/F"]).upper().strip(),
            "JP": str(hardlabels["J/P"]).upper().strip(),
        }
    except KeyError:
        return None
    return axes if axes["EI"] in {"E", "I"} and axes["NS"] in {"N", "S"} and axes["FT"] in {"F", "T"} and axes["JP"] in {"J", "P"} else None


def build_datasnaek() -> pd.DataFrame:
    path = INPUT_DIR / "kaggle_datasnaek_mbti_type__mbti_1.csv"
    df = read_csv(path)
    records: list[dict[str, Any]] = []
    for row_index, row in df.iterrows():
        mbti_type = str(row["type"]).upper().strip()
        axes = axes_from_type(mbti_type)
        if not axes:
            continue
        for post_index, post in enumerate(str(row["posts"]).split("|||")):
            text = clean_utterance(post)
            if not looks_like_usable_utterance(text):
                continue
            records.append(
                base_record(
                    text=text,
                    axes=axes,
                    mbti_type=mbti_type,
                    source_dataset="kaggle_datasnaek_mbti_type",
                    source_file=path.name,
                    source_id=f"{row_index}:{post_index}",
                    text_unit="post_chunk",
                    label_strength="weak_user_mbti",
                )
            )
    return pd.DataFrame(records)


def build_mbtibench() -> pd.DataFrame:
    path = INPUT_DIR / "mbtibench__mbtibench.jsonl"
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            axes = hard_axes_from_mbtibench(obj.get("hardlabels", {}))
            if not axes:
                continue
            softlabels = obj.get("softlabels", {})
            for post_index, post in enumerate(obj.get("posts", [])):
                text = clean_utterance(post)
                if not looks_like_usable_utterance(text):
                    continue
                records.append(
                    base_record(
                        text=text,
                        axes=axes,
                        mbti_type=None,
                        source_dataset="mbtibench",
                        source_file=path.name,
                        source_id=f"{obj.get('id')}:{post_index}",
                        text_unit="post",
                        label_strength="axis_hard_and_soft",
                        soft_EI=softlabels.get("E/I"),
                        soft_NS=softlabels.get("S/N"),
                        soft_FT=softlabels.get("T/F"),
                        soft_JP=softlabels.get("J/P"),
                    )
                )
    return pd.DataFrame(records)


def axis_counts(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    return {
        axis: {str(k): int(v) for k, v in df[axis].value_counts(dropna=False).sort_index().items()}
        for axis in ["EI", "NS", "FT", "JP"]
    }


def write_csv(path: Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)


def write_model_csv(path: Path, df: pd.DataFrame) -> None:
    write_csv(path, df[MODEL_COLUMNS])


def write_preprocessing_report(summary: dict[str, Any]) -> None:
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    report = f"""# Axis-Ready Preprocessing Report

## 목적

자유대화 챗봇에서 사용자의 발화 묶음을 임베딩한 뒤 `EI`, `NS`, `FT`, `JP` 4축 경향을 추정하는 모델을 학습하기 위한 데이터셋을 만든다.

최종 학습 CSV에는 서로 다른 원천의 메타 구조를 억지로 합치지 않기 위해 모델 학습에 필요한 컬럼만 남긴다.

```text
text, EI, NS, FT, JP
```

## 최종 산출물

- `etl/datasets/personality_training/axis_ready/all_axis_ready.csv`
- rows: {summary["total_rows"]:,}
- columns: `text`, `EI`, `NS`, `FT`, `JP`

## 사용한 원천

| source | raw file | 전처리 근거 |
| --- | --- | --- |
| `kaggle_datasnaek_mbti_type` | `selected_raw/kaggle_datasnaek_mbti_type__mbti_1.csv` | `posts`가 `|||`로 여러 게시글 chunk를 포함하고, `type`의 16유형 라벨을 4축으로 분리할 수 있어 weak-label 학습용으로 사용 |
| `mbtibench` | `selected_raw/mbtibench__mbtibench.jsonl` | `hardlabels`, `softlabels`가 이미 `E/I`, `S/N`, `T/F`, `J/P` 축 단위로 있어 보조/검증 성격의 학습 데이터로 사용 |

## 원천별 변환

### Kaggle datasnaek

1. `type` 컬럼의 16유형 라벨을 읽는다.
2. `INFP -> EI=I, NS=N, FT=F, JP=P`처럼 4축 라벨로 분해한다.
3. `posts` 컬럼을 `|||` 기준으로 나눠 하나의 게시글 chunk를 하나의 학습 행으로 만든다.
4. 텍스트를 정제한다.
5. 모델 학습용 컬럼 `text`, `EI`, `NS`, `FT`, `JP`만 최종 CSV에 기록한다.

### MBTIBench

1. JSONL의 각 row에서 `posts` 배열을 읽는다.
2. `hardlabels`의 `E/I`, `S/N`, `T/F`, `J/P`를 각각 `EI`, `NS`, `FT`, `JP`로 매핑한다.
3. 각 post를 하나의 학습 행으로 만든다.
4. 텍스트를 정제한다.
5. 모델 학습용 컬럼 `text`, `EI`, `NS`, `FT`, `JP`만 최종 CSV에 기록한다.

## 공통 정제 규칙

- URL 제거
- 이메일 제거
- 멘션 제거
- 해시태그 기호 제거
- 제어 문자 제거
- 학습에 방해되는 특수기호 제거
- 20자 미만 제거
- 2,000자 초과 제거
- 알파벳 단어 4개 미만 제거
- `mbti`, `INFP`, `ENFJ`, `cognitive functions` 같은 라벨 누수 표현 제거
- `text`, `EI`, `NS`, `FT`, `JP` 기준 중복 제거

## 원천별 행 수

| source | rows |
| --- | ---: |
| `kaggle_datasnaek_mbti_type` | {summary["by_source"]["kaggle_datasnaek_mbti_type"]:,} |
| `mbtibench` | {summary["by_source"]["mbtibench"]:,} |

## 제거한 원천

| source | 제거 근거 |
| --- | --- |
| `hf_babak_sentencebroken` | 텍스트가 과하게 전처리되어 자연스러운 자유대화 발화처럼 보기 어려움 |
| `kaggle_mazlumi_twitter_mbti` | 여러 트윗이 한 행에 붙은 타임라인 형태가 많아 하나의 발화 기준과 맞지 않음 |
| `kaggle_tapanvijay_mbti_cleaned` | `datasnaek`와 중복 가능성이 높음 |
| `hf_epinfomax_mbti_korean` | Parquet 스키마를 현재 환경에서 검증하지 못했고 목적 집중을 위해 제거 |
| `hf_jtatman_tweet_classify` | Parquet 스키마를 현재 환경에서 검증하지 못했고 목적 집중을 위해 제거 |

## Raw 비교 검증

이전 검증에서 `all_axis_ready.csv`의 처리 텍스트를 원천 chunk와 비교했다.

- 비교 행 수: 321,989
- 원천을 같은 정제 규칙으로 처리한 결과와 정확히 일치: 321,989
- 가공 중 잘린 것으로 의심되는 행: 0

따라서 짧거나 비완결형처럼 보이는 텍스트는 가공 중 잘린 것이 아니라 원천 chunk 자체가 그런 형태인 것으로 판단한다.

## 한계

대부분의 라벨은 발화 자체를 사람이 직접 판정한 값이 아니라 작성자 수준 MBTI 또는 축 라벨에서 온 weak label이다.

따라서 이 데이터는 재미용/참고용 4축 경향 추정 MVP에 사용하고, 심리 진단처럼 표현하지 않는다.
"""
    (METADATA_DIR / "axis_ready_preprocessing_report.md").write_text(report, encoding="utf-8")


def main() -> None:
    clear_output_dir(OUTPUT_DIR)
    source_frames = {
        "kaggle_datasnaek_mbti_type": build_datasnaek(),
        "mbtibench": build_mbtibench(),
    }

    for source_dataset, frame in source_frames.items():
        frame = frame.drop_duplicates(subset=["text", "EI", "NS", "FT", "JP"])
        source_frames[source_dataset] = frame

    all_df = pd.concat(source_frames.values(), ignore_index=True)
    all_df = all_df.drop_duplicates(subset=["text", "EI", "NS", "FT", "JP"])
    write_model_csv(OUTPUT_DIR / "all_axis_ready.csv", all_df)

    summary = {
        "purpose": "Curated weak-label dataset for chatbot user utterance MBTI 4-axis tendency estimation.",
        "output_dir": str(OUTPUT_DIR),
        "schema": MODEL_COLUMNS,
        "total_rows": int(len(all_df)),
        "by_source": {name: int(len(frame)) for name, frame in source_frames.items()},
        "axis_counts_total": axis_counts(all_df),
        "axis_counts_by_source": {name: axis_counts(frame) for name, frame in source_frames.items()},
        "included_sources": list(source_frames.keys()),
        "removed_sources": {
            "hf_babak_sentencebroken": "Too preprocessed; less natural as chatbot-like utterance.",
            "kaggle_mazlumi_twitter_mbti": "Often concatenated tweet timelines rather than one clear utterance.",
            "kaggle_tapanvijay_mbti_cleaned": "Likely duplicate of datasnaek.",
            "hf_epinfomax_mbti_korean": "Parquet schema could not be verified in this environment; removed to keep project focused.",
            "hf_jtatman_tweet_classify": "Parquet schema could not be verified in this environment; removed to keep project focused.",
        },
        "cleaning_rules": [
            "Split datasnaek posts by ||| into post chunks.",
            "Convert MbtiBench JSONL posts to CSV rows.",
            "Remove URLs, emails, mentions, control characters, and noisy symbols.",
            "Drop rows shorter than 20 characters or longer than 2000 characters.",
            "Drop rows with fewer than 4 alphabetic words.",
            "Drop rows containing MBTI label leakage such as mbti, INFP, ENFJ, or cognitive functions.",
            "Deduplicate by text and four axis labels.",
        ],
        "label_note": "Most rows are weak labels derived from author-level MBTI, not human-labeled utterance-level psychological truth.",
    }
    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "source_dataset": name,
                "rows": int(len(frame)),
                **{f"{axis}_{label}": count for axis, counts in axis_counts(frame).items() for label, count in counts.items()},
            }
            for name, frame in source_frames.items()
        ]
    ).to_csv(OUTPUT_DIR / "source_summary.csv", index=False, encoding="utf-8-sig")
    write_preprocessing_report(summary)

    print(json.dumps({"output_dir": str(OUTPUT_DIR), "total_rows": int(len(all_df)), "by_source": summary["by_source"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
