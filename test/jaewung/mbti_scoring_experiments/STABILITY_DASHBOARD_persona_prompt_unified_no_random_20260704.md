# MBTI Scoring Stability Dashboard

같은 backend 월간 데모 데이터에서 방안별 최종 MBTI와 축별 점수 흔들림을 비교한다.

서로 다른 실행 모드가 섞이면 안정성이 왜곡될 수 있으므로 `strategy + mode` 단위로 분리해 표시한다.

| 방식 | 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| persona_direct | demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v5_persona_prompt_unified_no_random_20260704_01 / persona_py_prompt_source_v1_20260704 / llm / custom / openai:gpt-5.4-mini | 주의 | 50 | ISFP | 100.0% | 1 | 0.1170 | 5.8523 | SN:N->S |
| rubric_code | no_data | 데이터없음 | 0 |  | 0.0% | 0 | 0.0000 | 0.0000 | 변화 없음 |
| triple_majority | no_data | 데이터없음 | 0 |  | 0.0% | 0 | 0.0000 | 0.0000 | 변화 없음 |
| hundred_point_ensemble | no_data | 데이터없음 | 0 |  | 0.0% | 0 | 0.0000 | 0.0000 | 변화 없음 |
| triple_supervisor | demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v5_persona_prompt_unified_no_random_20260704_01 / persona_py_triple_supervisor_v1_20260704 / llm / custom / openai:gpt-5.4-mini / judges=openai:gpt-5.4-mini; openai:gpt-5.4-mini; openai:gpt-5.4-mini / supervisor=rule:mode_if_available_else_median | 주의 | 50 | ISFP | 98.0% | 2 | 0.1082 | 5.4083 | SN:N->S |

표준편차 판정: axis_avg는 0.05 이하 안정, 0.15 이하 주의, 초과 불안정으로 본다. 표시점수는 3점 이하 안정, 8점 이하 주의, 초과 불안정으로 본다.

각 방안의 원본 결과는 해당 폴더의 `results/mbti_score_changes_persona_prompt_unified_no_random_20260704.csv`에서 확인한다.
각 방안의 상세 축별 안정성은 해당 폴더의 `results/STABILITY_REPORT_persona_prompt_unified_no_random_20260704.md`에서 확인한다.
