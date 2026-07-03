# 감정분류 (6감정 → 4공감모드)

KcELECTRA 임베딩(freeze) → 분류기(LogReg / LinearSVM / XGBoost 비교) 파이프라인.
6감정으로 분류한 뒤 4공감모드로 매핑한다. 파인튜닝은 하지 않는다(가볍고 빠른 freeze 임베딩).

- **6감정**: 분노 · 슬픔 · 불안 · 상처 · 당황 · 기쁨
- **4공감모드**: 화남 · 속상 · 계획 · 응원
- **매핑**: 분노→화남 · 슬픔→속상 · 불안→계획 · 상처→응원 · 당황→속상 · 기쁨→응원

## 1. 데이터 생성

AI Hub 감성대화 + KOTE를 병합해 `{"text", "emotion"}` jsonl 생성.

```bash
python build_emotion_dataset.py --out ../../data/kcelectra_train_clean.jsonl
```

## 2. 학습

> KcELECTRA 임베딩은 GPU가 빠르다. 전체(약 5.8만건)는 PC/Colab 권장.

```bash
# 빠른 점검(감정별 5천건 샘플)
python train_emotion_4mode.py --data ../../data/kcelectra_train_clean.jsonl --label-col emotion --sample 5000

# 전체 학습
python train_emotion_4mode.py --data ../../data/kcelectra_train_clean.jsonl --label-col emotion
```

필요 패키지: `torch transformers scikit-learn xgboost joblib pandas`

## 3. 산출물 (`artifacts/`)

- `logreg_emo4.joblib` · `linearsvm_emo4.joblib` · `xgb_emo4.joblib` — 분류기
- `label_encoder.joblib` — XGBoost용 라벨 인코더
- **`metrics.json`** — best 모델·임베딩 설정·지표·신뢰도. 백엔드가 이걸 읽어 자동 로드하고, 발표용 실측 수치도 여기서 가져온다.

## 4. 백엔드 연결

`ai/emotion/emotion_model.py`가 `artifacts/`를 자동 로드해 추론한다.
`predict_emotion`은 **학습 모델 1순위 → 없으면 LLM 폴백** 구조라, 산출물만 놓으면 자동 전환된다.

- 산출물 위치: 기본 `ai/emotion/artifacts/` (또는 환경변수 `EMOTION_ARTIFACT_DIR`로 지정)
- 백엔드 환경에도 `torch transformers xgboost joblib` 필요. (없으면 자동으로 LLM 폴백)
- 추론 결과(4감정)는 `emotion_label`(기쁨·슬픔·분노·일반)로 에이전트 라우팅에 사용된다.

## 5. 평가지표 (목표)

- 4모드 Macro-F1 ≥ 0.80 (실KPI), 6감정은 참고치
- `metrics.json`에 클래스별 리포트·신뢰도 기록 → `[개별] 평가지표_김한솔.md` 기준과 대조
