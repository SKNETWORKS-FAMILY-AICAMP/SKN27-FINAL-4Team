# MBTI Scoring Stability Dashboard

같은 backend 월간 데모 데이터에서 방안별 최종 MBTI와 축별 점수 흔들림을 비교한다.

서로 다른 실행 모드가 섞이면 안정성이 왜곡될 수 있으므로 `strategy + mode` 단위로 분리해 표시한다.

| 방식 | 모드 | 판정 | 실행 수 | 최빈 최종 MBTI | MBTI 안정률 | MBTI 종류 수 | 최대 axis_avg 표준편차 | 최대 표시점수 표준편차 | 최빈 변화 축 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| persona_direct | demo_questions_v2_axis5_20260703 / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 50 | ISFJ | 82.0% | 2 | 0.1698 | 7.8288 | SN:N->S; JP:P->J |
| persona_direct | demo_questions_v2_axis5_20260703 / legacy_run_batch / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 주의 | 50 | ISFJ | 98.0% | 2 | 0.1486 | 7.4227 | SN:N->S; JP:P->J |
| persona_direct | demo_questions_v3_jp_p_adjusted_20260703 / legacy_run_batch / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 53 | ISFP | 100.0% | 1 | 0.1972 | 9.8602 | SN:N->S |
| persona_direct | demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v4_persona_openai_independent_20260703_01 / persona_axis_scoring_conservative_v1_20260703 / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 50 | ISFP | 100.0% | 1 | 0.1551 | 7.7383 | SN:N->S |
| persona_direct | legacy_demo_dataset / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 20 | INFP | 70.0% | 2 | 0.1921 | 5.5846 | JP:P->J |
| rubric_code | demo_questions_v2_axis5_20260703 / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 불안정 | 24 | ISFJ | 62.5% | 4 | 0.2127 | 5.5895 | SN:N->S; JP:P->J |
| rubric_code | legacy_demo_dataset / legacy_run_batch / legacy_prompt_version / llm / single_1_openai_baseline / openai:gpt-5.4-mini | 주의 | 20 | INFJ | 100.0% | 1 | 0.1054 | 5.3094 | JP:P->J |
| triple_majority | no_data | 데이터없음 | 0 |  | 0.0% | 0 | 0.0000 | 0.0000 | 변화 없음 |
| hundred_point_ensemble | no_data | 데이터없음 | 0 |  | 0.0% | 0 | 0.0000 | 0.0000 | 변화 없음 |
| triple_supervisor | demo_questions_v4_jp_mixed_j_rebalanced_20260703 / v4_persona_openai_independent_20260703_01 / placeholder_prompt_na / placeholder / custom / openai:gpt-5.4-mini | 안정 | 2 | ISFJ | 100.0% | 1 | 0.0000 | 0.0000 | SN:N->S; JP:P->J |

표준편차 판정: axis_avg는 0.05 이하 안정, 0.15 이하 주의, 초과 불안정으로 본다. 표시점수는 3점 이하 안정, 8점 이하 주의, 초과 불안정으로 본다.

각 방안의 상세 축별 안정성은 해당 폴더의 `results/STABILITY_REPORT.md`에서 확인한다.
