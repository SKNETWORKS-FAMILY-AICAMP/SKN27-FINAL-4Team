# Source Data

This folder stores original or source-level datasets needed for reproducibility.

## Contents

| path | source | note |
| --- | --- | --- |
| `kaggle_datasnaek_mbti_type/` | Kaggle `datasnaek/mbti-type` | English MBTI posts dataset. |
| `mbtibench/` | MBTIBench | English MBTI benchmark records in JSONL format. |
| `huggingface_epinfomax_mbti_korean_dataset/` | Hugging Face `epinfomax/mbti-korean-dataset` | Korean MBTI dataset. Original Parquet split files are under `data/`. |
| `manifest.csv`, `manifest.json`, `summary.json` | local metadata | Source inventory and summary. |

Do not edit source files directly. Derived CSVs and modeling-ready files should live in sibling folders.
