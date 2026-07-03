# rubric_code Stability Report

## 모드별 요약

| 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| demo_questions_v2_axis5_20260703 / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 24 | ISFJ | 62.5% | 4 | 0.2127 | 5.5895 | SN:N->S; JP:P->J |
| legacy_demo_dataset / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 주의 | 20 | INFJ | 100.0% | 1 | 0.1054 | 5.3094 | JP:P->J |

## 축별 안정성

### demo_questions_v2_axis5_20260703 / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 70.8% | 2 | 5.5895 | 0.2127 |
| SN | S | 100.0% | 1 | 2.6021 | 0.0520 |
| TF | F | 100.0% | 1 | 2.5000 | 0.0500 |
| JP | J | 83.3% | 2 | 1.9432 | 0.1286 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.2127 → 높음(불안정)
- max 표시점수 표준편차: 5.5895 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 높음(불안정) | 보통(주의) |
| SN | 보통(주의) | 낮음(안정) |
| TF | 낮음(안정) | 낮음(안정) |
| JP | 보통(주의) | 낮음(안정) |

### legacy_demo_dataset / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini

| 축 | 최빈 글자 | 글자 안정률 | 글자 종류 수 | 표시점수 표준편차 | axis_avg 표준편차 |
| --- | --- | --- | --- | --- | --- |
| IE | I | 100.0% | 1 | 2.5981 | 0.0541 |
| SN | N | 100.0% | 1 | 3.6742 | 0.0735 |
| TF | F | 100.0% | 1 | 2.5495 | 0.0510 |
| JP | J | 100.0% | 1 | 5.3094 | 0.1054 |

#### 표준편차 판정

- max axis_avg 표준편차: 0.1054 → 보통(주의)
- max 표시점수 표준편차: 5.3094 → 보통(주의)
- 해석: 표준편차가 낮을수록 같은 데이터 반복 실행에서 점수 흔들림이 작아 안정적이다.

| 축 | axis_avg 판정 | 표시점수 판정 |
| --- | --- | --- |
| IE | 보통(주의) | 낮음(안정) |
| SN | 보통(주의) | 보통(주의) |
| TF | 보통(주의) | 낮음(안정) |
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
