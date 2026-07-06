# triple_supervisor Stability Report

## 모드별 요약

| 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v5_persona_prompt_unified_no_random_20260704_01 / persona_py_triple_supervisor_v1_20260704 / llm / custom / openai:gpt-5.4-mini / judges=openai:gpt-5.4-mini; openai:gpt-5.4-mini; openai:gpt-5.4-mini / supervisor=rule:mode_if_available_else_median | 주의 | 50 | ISFP | 98.0% | 2 | 0.1082 | 5.4083 | SN:N->S |

## 축별 안정성

### demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v5_persona_prompt_unified_no_random_20260704_01 / persona_py_triple_supervisor_v1_20260704 / llm / custom / openai:gpt-5.4-mini / judges=openai:gpt-5.4-mini; openai:gpt-5.4-mini; openai:gpt-5.4-mini / supervisor=rule:mode_if_available_else_median

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 5.4083 | 0.1082 |
| SN | S | 100.0% | 1 | 3.7417 | 0.0748 |
| TF | F | 100.0% | 1 | 2.2383 | 0.0448 |
| JP | P | 98.0% | 2 | 3.8730 | 0.0924 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1082 → 보통(주의)
- max 표시점수 표준편차: 5.4083 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 보통(주의) | 보통(주의) |
| SN | 보통(주의) | 보통(주의) |
| TF | 낮음(안정) | 낮음(안정) |
| JP | 보통(주의) | 보통(주의) |

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
