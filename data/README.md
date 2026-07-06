# data/ — 학습 데이터셋

## ⚠️ kcelectra_train_clean.jsonl 은 repo에 포함되지 않습니다

감정분류 학습 정제본(58,234건)은 **AI Hub 감성대화 말뭉치의 파생물**입니다.
AI Hub 이용약관상 데이터는 AI Hub를 통해서만 제공되어야 하며 **제3자 재배포가 금지**되므로,
공개 repo에는 데이터 대신 **재생성 스크립트**를 배포합니다.

### 재생성 방법

1. [AI Hub 감성대화 말뭉치](https://aihub.or.kr) 다운로드 (Training/Validation 221115_add, 라벨링데이터)
2. 스크립트 실행:

```bash
python ai/emotion/rebuild_clean_dataset.py --raw "<다운로드 경로>/018.감성대화"
```

3. `data/kcelectra_train_clean.jsonl` 생성 확인 (58,234건)

재현성은 원 정제본 대비 **순서·내용 100% 일치**로 검증됨 — 분석 과정과 정제 규칙의 근거는
`ai/emotion/EDA_감정분류_김한솔.ipynb` (§0-2 계보 검증, §7 정제 결정) 참조.

### 데이터 명세

| 파일 | 내용 | 출처 |
|---|---|---|
| `kcelectra_train_clean.jsonl` (로컬 생성) | `{"text", "emotion"}` × 58,234 — 첫 사람 발화 + 6감정 대분류 | AI Hub 감성대화 (재배포 금지) |

(구 `safety_redteam_set.json`·`scale_gold_set.json`·`scales/`는 미사용으로 제거 — 2026-07-03)
