# Axis-Ready Preprocessing Report

## 목적

자유대화 챗봇에서 사용자의 발화 묶음을 임베딩한 뒤 `EI`, `NS`, `FT`, `JP` 4축 경향을 추정하는 모델을 학습하기 위한 데이터셋을 만든다.

최종 학습 CSV에는 서로 다른 원천의 메타 구조를 억지로 합치지 않기 위해 모델 학습에 필요한 컬럼만 남긴다.

```text
text, EI, NS, FT, JP
```

## 최종 산출물

- `etl/datasets/personality_training/axis_ready/all_axis_ready.csv`
- rows: 321,989
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
| `kaggle_datasnaek_mbti_type` | 315,182 |
| `mbtibench` | 7,819 |

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
