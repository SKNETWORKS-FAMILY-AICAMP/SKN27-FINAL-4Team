# ETL

데이터 수집, 선별, 전처리 산출물을 관리한다.

## 현재 유지 기준

- `datasets/personality_training/selected_raw/`: 최종 학습 데이터 재현에 필요한 원천 2종
- `datasets/personality_training/axis_ready/all_axis_ready.csv`: 모델 학습 후보 통합본
- `datasets/personality_training/axis_ready/summary.json`: 최종 데이터 요약
- `datasets/personality_training/metadata/`: 선별/검증 근거
- `scripts/datasets/build_mbti_axis_ready_dataset.py`: 원천에서 최종 통합 CSV를 재생성
- `scripts/datasets/validate_axis_ready_against_raw.py`: 원천과 최종 통합 CSV 일치 여부 검증

## 재현

```powershell
python etl\scripts\datasets\build_mbti_axis_ready_dataset.py
python etl\scripts\datasets\validate_axis_ready_against_raw.py
```
