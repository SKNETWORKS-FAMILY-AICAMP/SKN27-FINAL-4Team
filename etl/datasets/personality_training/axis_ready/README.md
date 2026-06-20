# Axis Ready Dataset

모델 학습에 필요한 최소 컬럼만 남긴 최종 통합 데이터셋이다.

## Files

| file | description |
| --- | --- |
| `all_axis_ready.csv` | 최종 학습 후보 통합본 |
| `summary.json` | 전체 행 수, 축 분포, 포함/제거 원천 요약 |
| `source_summary.csv` | 원천별 행 수와 축 분포 |

## Schema

```text
text, EI, NS, FT, JP
```

각 축 값은 문자 라벨을 사용한다.

- `EI`: `E` or `I`
- `NS`: `N` or `S`
- `FT`: `F` or `T`
- `JP`: `J` or `P`

## Note

대부분의 라벨은 발화 자체를 사람이 직접 판정한 값이 아니라 작성자 수준 MBTI 또는 축 라벨에서 온 weak label이다. 심리 진단이 아니라 재미용/참고용 경향 추정 MVP 데이터로만 사용한다.
