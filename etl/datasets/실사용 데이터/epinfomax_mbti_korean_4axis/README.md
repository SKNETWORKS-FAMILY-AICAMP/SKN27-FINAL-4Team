# epinfomax MBTI Korean 4-Axis Dataset

Hugging Face `epinfomax/mbti-korean-dataset` source files converted for MBTI tendency modeling.

The original train, validation, and test split assignments are preserved. This ready-to-use version sanitizes `text` for embedding, restores the 16-type MBTI label, and adds four binary axis labels.

## Source

- Dataset: https://huggingface.co/datasets/epinfomax/mbti-korean-dataset
- Label mapping: https://huggingface.co/datasets/epinfomax/mbti-korean-dataset/blob/main/train_hf_skills.py
- Raw files: `etl/datasets/원천 데이터/huggingface_epinfomax_mbti_korean_dataset/`
- Intermediate CSV files: `etl/datasets/중간 가공 데이터/huggingface_epinfomax_mbti_korean_dataset_csv/`

## Files

| file | rows |
| --- | ---: |
| `huggingface_epinfomax_mbti_korean_4axis_train.csv` | 14,550 |
| `huggingface_epinfomax_mbti_korean_4axis_validation.csv` | 1,819 |
| `huggingface_epinfomax_mbti_korean_4axis_test.csv` | 1,821 |
| `summary.json` | metadata |

## Columns

| column | description |
| --- | --- |
| `text` | Embedding-ready Korean text |
| `label` | Original integer label from the dataset |
| `mbti_type` | Restored 16-type MBTI label |
| `EI` | `E` or `I` |
| `NS` | `N` or `S` |
| `FT` | `F` or `T` |
| `JP` | `J` or `P` |

## Text Sanitization Policy

Rows are not removed just because they contain English letters, digits, symbols, or MBTI terms. Those characters are removed inside `text`, and the row is kept when enough Korean context remains.

The script:

- Collapses whitespace and trims leading/trailing spaces.
- Removes URL-like spans.
- Removes direct 16-type MBTI names, including forms attached to Korean particles or English letters.
- Removes generic MBTI leakage terms such as `MBTI`, `엠비티아이`, and `성격유형`.
- Removes Korean MBTI aliases such as `엔프피`, `인프피`, `잇팁`, and `엣팁`.
- Removes all English letters.
- Keeps digits because age, duration, count, order, and time expressions can preserve context.
- Keeps conservative emotion markers: `?`, `!`, `~`, `.`, `ㅋ`, `ㅎ`, `ㅜ`, and `ㅠ`.
- Repairs spacing around selected emotion markers, such as `. .`, `.. !`, and ` ?`.
- Removes conservative orphan pronoun connectives after MBTI-term removal, such as `저는 인데` and `저는 라서`.
- Collapses repeated emotion markers to at most 3 characters.
- Removes other symbols and punctuation.
- Keeps Korean characters, digits, selected emotion markers, and spaces.
- Drops only rows whose sanitized text has fewer than 5 Korean/digit context characters.

## Minimum Data Requirement

The intended model is four independent binary classifiers over text embeddings: `EI`, `NS`, `FT`, and `JP`.

The current practical minimum is:

| split | total rows | minimum rows per class in every axis |
| --- | ---: | ---: |
| train | 8,000 | 2,000 |
| validation | 1,000 | 250 |
| test | 1,000 | 250 |

The current sanitized files stay above the minimum.

## Row Summary

| split | original rows | ready-to-use rows | removed after sanitization |
| --- | ---: | ---: | ---: |
| train | 14,564 | 14,550 | 14 |
| validation | 1,820 | 1,819 | 1 |
| test | 1,821 | 1,821 | 0 |

Most previously removed rows are restored because English, MBTI terms, digits, and symbols are now removed inside `text` rather than by dropping the whole row.

## MBTI Leakage Terms

The preprocessing script removes these direct MBTI hints inside `text`:

- English 16-type names: `ENFJ`, `ENFP`, `ENTJ`, `ENTP`, `ESFJ`, `ESFP`, `ESTJ`, `ESTP`, `INFJ`, `INFP`, `INTJ`, `INTP`, `ISFJ`, `ISFP`, `ISTJ`, `ISTP`
- Generic terms: `MBTI`, `엠비티아이`, `성격유형`
- Korean aliases: `엔프제`, `엔프피`, `엔티제`, `엔팁`, `엣프제`, `엣프피`, `엣티제`, `엣팁`, `인프제`, `인프피`, `인티제`, `인팁`, `잇프제`, `잇프피`, `잇티제`, `잇팁`

## Reproduce

```powershell
$env:UV_CACHE_DIR = '.uv-cache'
uv run python etl\scripts\personality_training\preprocess_epinfomax_korean_4axis.py
```
