# Personality Training Dataset

자유대화 챗봇 발화에서 MBTI 4축 경향(`EI`, `NS`, `FT`, `JP`)을 추정하기 위한 약지도 학습 후보 데이터셋이다.

## 구조

| folder | role |
| --- | --- |
| `selected_raw/` | 최종 선별된 원천 데이터. 재현을 위해 보관한다. |
| `axis_ready/` | 모델 학습에 바로 넣을 수 있는 최종 통합 CSV와 요약. |
| `metadata/` | 원천 선별, 전처리, 검증 근거. |

## 유지한 원천

| source | file | reason |
| --- | --- | --- |
| `kaggle_datasnaek_mbti_type` | `selected_raw/kaggle_datasnaek_mbti_type__mbti_1.csv` | 게시글 chunk 단위로 분리 가능하고 16유형 라벨을 4축으로 변환할 수 있다. |
| `mbtibench` | `selected_raw/mbtibench__mbtibench.jsonl` | `E/I`, `S/N`, `T/F`, `J/P` 축 단위 hard/soft label을 제공한다. |

## 최종 산출물

- `axis_ready/all_axis_ready.csv`
- `axis_ready/summary.json`
- `axis_ready/source_summary.csv`

## 재현

```powershell
python etl\scripts\datasets\build_mbti_axis_ready_dataset.py
python etl\scripts\datasets\validate_axis_ready_against_raw.py
```
