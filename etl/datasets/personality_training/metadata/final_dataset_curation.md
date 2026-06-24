# Personality Training Dataset Curation

## Goal

Prepare data for a model that estimates MBTI axis tendencies from user utterances or chatbot conversation logs.

The intended modeling flow is:

```text
text -> embedding model -> EI / NS / FT / JP prediction
```

Only the `text` column should be embedded. Label columns should be kept as supervised targets.

## Folder Policy

| stage | folder | content |
| --- | --- | --- |
| source | `etl/datasets/원천 데이터/` | Original or source-level datasets. |
| intermediate | `etl/datasets/중간 가공 데이터/` | First-pass converted files, such as Parquet converted to CSV. |
| ready-to-use | `etl/datasets/실사용 데이터/` | Cleaned files intended for embedding and model training. |

## Selected Korean Dataset

The primary Korean dataset is Hugging Face `epinfomax/mbti-korean-dataset`.

Source structure:

| column | meaning |
| --- | --- |
| `text` | Korean source text |
| `label` | integer MBTI label |

The integer labels are restored to 16 MBTI types with the dataset training script mapping, then split into four axis labels:

```text
mbti_type -> EI, NS, FT, JP
```

## Ready-to-Use Output

`etl/datasets/실사용 데이터/epinfomax_mbti_korean_4axis/`

| file | rows |
| --- | ---: |
| `huggingface_epinfomax_mbti_korean_4axis_train.csv` | 14,550 |
| `huggingface_epinfomax_mbti_korean_4axis_validation.csv` | 1,819 |
| `huggingface_epinfomax_mbti_korean_4axis_test.csv` | 1,821 |

Columns:

```text
text,label,mbti_type,EI,NS,FT,JP
```

## Current Text Policy

- Preserve the original train, validation, and test split assignments.
- Remove leakage/noise characters inside `text` instead of dropping whole rows.
- Remove direct MBTI type names, Korean MBTI aliases, generic MBTI terms, English letters, URLs, and non-emotional symbols.
- Keep Korean characters, digits, spaces, and conservative emotion markers: `?`, `!`, `~`, `.`, `ㅋ`, `ㅎ`, `ㅜ`, and `ㅠ`.
- Collapse repeated emotion markers to at most 3 characters.

Korean MBTI aliases are treated as direct label leakage. The current alias list is:

```text
엔프제, 엔프피, 엔티제, 엔팁
엣프제, 엣프피, 엣티제, 엣팁
인프제, 인프피, 인티제, 인팁
잇프제, 잇프피, 잇티제, 잇팁
```
- Drop only rows whose sanitized text has fewer than 5 Korean/digit context characters.

## Scripts

All personality-training preprocessing scripts are collected under:

`etl/scripts/personality_training/`

Current script:

`etl/scripts/personality_training/preprocess_epinfomax_korean_4axis.py`

## Limitation

This dataset is useful for an MBTI tendency estimator, but it should not be treated as a clinical or definitive personality diagnosis dataset. Model outputs should be presented as tendency scores, not fixed identity labels.
