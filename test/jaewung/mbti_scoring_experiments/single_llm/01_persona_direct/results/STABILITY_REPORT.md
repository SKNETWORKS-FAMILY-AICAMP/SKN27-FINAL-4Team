# persona_direct Stability Report

## 모드별 요약

| 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| demo_questions_v2_axis5_20260703 / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 50 | ISFJ | 82.0% | 2 | 0.1698 | 7.8288 | SN:N->S; JP:P->J |
| demo_questions_v2_axis5_20260703 / legacy_run_batch / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 주의 | 50 | ISFJ | 98.0% | 2 | 0.1486 | 7.4227 | SN:N->S; JP:P->J |
| demo_questions_v3_jp_p_adjusted_20260703 / legacy_run_batch / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 53 | ISFP | 100.0% | 1 | 0.1972 | 9.8602 | SN:N->S |
| demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v4_persona_openai_independent_20260703_01 / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 50 | ISFP | 100.0% | 1 | 0.1551 | 7.7383 | SN:N->S |
| legacy_demo_dataset / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 20 | INFP | 70.0% | 2 | 0.1921 | 5.5846 | JP:P->J |

## 축별 안정성

### demo_questions_v2_axis5_20260703 / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 7.5901 | 0.1518 |
| SN | S | 100.0% | 1 | 7.8288 | 0.1566 |
| TF | F | 100.0% | 1 | 3.6346 | 0.0727 |
| JP | J | 82.0% | 2 | 3.5000 | 0.1698 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1698 → 높음(불안정)
- max 표시점수 표준편차: 7.8288 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 높음(불안정) | 보통(주의) |
| SN | 높음(불안정) | 보통(주의) |
| TF | 보통(주의) | 보통(주의) |
| JP | 높음(불안정) | 보통(주의) |

### demo_questions_v2_axis5_20260703 / legacy_run_batch / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 7.4227 | 0.1486 |
| SN | S | 100.0% | 1 | 7.3655 | 0.1473 |
| TF | F | 100.0% | 1 | 3.3166 | 0.0663 |
| JP | J | 98.0% | 2 | 3.1625 | 0.0883 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1486 → 보통(주의)
- max 표시점수 표준편차: 7.4227 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 보통(주의) | 보통(주의) |
| SN | 보통(주의) | 보통(주의) |
| TF | 보통(주의) | 보통(주의) |
| JP | 보통(주의) | 보통(주의) |

### demo_questions_v3_jp_p_adjusted_20260703 / legacy_run_batch / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 8.9824 | 0.1798 |
| SN | S | 100.0% | 1 | 9.8602 | 0.1972 |
| TF | F | 100.0% | 1 | 2.7472 | 0.0549 |
| JP | P | 100.0% | 1 | 7.9290 | 0.1586 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1972 → 높음(불안정)
- max 표시점수 표준편차: 9.8602 → 높음(불안정)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 높음(불안정) | 높음(불안정) |
| SN | 높음(불안정) | 높음(불안정) |
| TF | 보통(주의) | 낮음(안정) |
| JP | 높음(불안정) | 보통(주의) |

### demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v4_persona_openai_independent_20260703_01 / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 7.7383 | 0.1551 |
| SN | S | 100.0% | 1 | 6.5490 | 0.1310 |
| TF | F | 100.0% | 1 | 3.5833 | 0.0717 |
| JP | P | 100.0% | 1 | 4.5535 | 0.0912 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1551 → 높음(불안정)
- max 표시점수 표준편차: 7.7383 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 높음(불안정) | 보통(주의) |
| SN | 보통(주의) | 보통(주의) |
| TF | 보통(주의) | 보통(주의) |
| JP | 보통(주의) | 보통(주의) |

### legacy_demo_dataset / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 4.8415 | 0.0950 |
| SN | N | 100.0% | 1 | 5.5846 | 0.1117 |
| TF | F | 100.0% | 1 | 3.6315 | 0.0726 |
| JP | P | 70.0% | 2 | 4.5000 | 0.1921 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1921 → 높음(불안정)
- max 표시점수 표준편차: 5.5846 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 보통(주의) | 보통(주의) |
| SN | 보통(주의) | 보통(주의) |
| TF | 보통(주의) | 보통(주의) |
| JP | 높음(불안정) | 보통(주의) |

## 판정 기준

| 판정 | 기준 |
| --- | --- |
| 안정 | 최종 MBTI가 1종이고 최대 axis_avg 표준편차가 0.05 이하 |
| 주의 | 최종 MBTI가 2종 이하, 최빈 MBTI 비율 80% 이상, 최대 axis_avg 표준편차 0.15 이하 |
| 불안정 | 위 기준을 벗어남 |

## 표준편차 해석 기준

| 지표 | 낮음(안정) | 보통(주의) | 높음(불안정) |
| --- | --- | --- | --- |
| axis_avg 표준편차 | 0.0500 이하 | 0.1500 이하 | 0.1500 초과 |
| 표시점수 표준편차 | 3.0000 이하 | 8.0000 이하 | 8.0000 초과 |
