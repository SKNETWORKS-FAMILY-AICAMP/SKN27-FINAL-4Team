# ETL

Project data collection, source preservation, intermediate conversion, and final training data live under `etl/`.

## Dataset Folders

| folder | role |
| --- | --- |
| `datasets/원천 데이터/` | Original or source-level datasets kept for reproducibility. |
| `datasets/중간 가공 데이터/` | First-pass converted files, such as Parquet converted to CSV. |
| `datasets/실사용 데이터/` | Final datasets intended for modeling or embedding. |
| `datasets/personality_training/metadata/` | Notes and curation records for personality training data. |

## Scripts

All personality-training preprocessing scripts are collected in:

`scripts/personality_training/`

## Current Main Dataset

The Korean MBTI training dataset ready for embedding is:

`datasets/실사용 데이터/epinfomax_mbti_korean_4axis/`

Reproduce it with:

```powershell
$env:UV_CACHE_DIR = '.uv-cache'
uv run python etl\scripts\personality_training\preprocess_epinfomax_korean_4axis.py
```
