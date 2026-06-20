# Final Dataset Curation

## Intent

자유대화 챗봇 발화에서 MBTI 4축 경향을 가볍게 추정하기 위한 약지도 학습 후보 데이터셋을 만든다.

최종 모델 입력 스키마는 다음 5개 컬럼으로 제한한다.

```text
text, EI, NS, FT, JP
```

## Kept Sources

| source | reason |
| --- | --- |
| `kaggle_datasnaek_mbti_type` | `posts`를 `|||` 기준 chunk로 나눌 수 있고, 16유형 라벨을 4축 라벨로 변환할 수 있다. |
| `mbtibench` | `E/I`, `S/N`, `T/F`, `J/P` hard/soft label이 있어 보조 학습/검증 원천으로 적합하다. |

## Removed Sources

| source | reason |
| --- | --- |
| `hf_babak_sentencebroken` | 문장 단위로 과하게 가공되어 자유대화 발화 chunk로 보기 어렵다. |
| `kaggle_mazlumi_twitter_mbti` | 여러 트윗이 한 행에 붙은 타임라인 형태가 많아 단일 발화 기준과 맞지 않는다. |
| `kaggle_tapanvijay_mbti_cleaned` | `datasnaek`와 중복 가능성이 높다. |
| `hf_epinfomax_mbti_korean` | 현재 환경에서 Parquet 스키마 검증이 되지 않았고 MVP 범위를 좁히기 위해 제외했다. |
| `hf_jtatman_tweet_classify` | 현재 환경에서 Parquet 스키마 검증이 되지 않았고 MVP 범위를 좁히기 위해 제외했다. |

## Final Data

- Final CSV: `etl/datasets/personality_training/axis_ready/all_axis_ready.csv`
- Total rows: 321,989
- `kaggle_datasnaek_mbti_type`: 315,182
- `mbtibench`: 7,819

## Validation

- MBTI label leakage in `text`: 0
- Text shorter than 20 characters: 0
- Text longer than 2,000 characters: 0
- Rows regenerated from selected raw sources match the final CSV exactly.

## Limitation

대부분의 라벨은 발화 자체를 사람이 직접 판정한 값이 아니라 작성자 수준 MBTI 또는 축 라벨에서 온 weak label이다. 이 데이터셋은 재미용/참고용 4축 경향 추정 MVP에 사용하고, 심리 진단처럼 표현하지 않는다.
