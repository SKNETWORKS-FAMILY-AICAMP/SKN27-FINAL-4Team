# MBTI Scoring Experiments

월간 MBTI 응답별 점수화 후보를 실제 backend 월간 파이프라인 기준으로 비교하기 위한 수동 실행용 실험 폴더다.

운영 파이프라인인 `app/backend/mbti/services/monthly_pipeline.py`를 import해서 같은 데모 월간 Q&A와 같은 baseline으로 실행한다. 각 안정화 방안은 scoring client만 교체하고, 1차 개시, 2차 개시, 그래프 점수 계산, 최종 MBTI 조합, 리포트 생성 흐름은 backend 서비스 파이프라인을 그대로 탄다.

## 구조

| 경로 | 역할 |
| --- | --- |
| `strategies.py` | 후보 채점 방식의 공통 인터페이스와 전략 구현 |
| `run_experiment.py` | backend 월간 파이프라인을 호출하는 공통 실행 엔진 |
| `01_persona_direct/` | 페르소나 기반 직접 채점 실험 |
| `02_rubric_code/` | 루브릭코드 기반 채점 실험 |
| `03_triple_majority/` | 3자 LLM 다수결 실험 |
| `04_hundred_point_ensemble/` | 100점제 앙상블 구간 다수결 실험 |
| `05_triple_supervisor/` | 3자 LLM 슈퍼바이저 실험 |

## 실행

전체 방식을 한 번에 실행하면 각 방안 폴더의 `results/mbti_score_changes.csv`에 실행별 결과가 따로 저장되고, 안정성 요약 파일도 자동 갱신된다.

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py
```

특정 방식만 실행할 수도 있다.

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py --strategy persona_direct
```

각 방안 폴더의 `run.py`를 직접 실행해도 같은 결과를 얻을 수 있다.

```powershell
python test\jaewung\mbti_scoring_experiments\01_persona_direct\run.py
```

기본 실행은 외부 API를 호출하지 않는다. 다만 전체 월간 흐름은 실제 backend `run_monthly_mbti_pipeline()`을 사용한다. 기본 전략들은 scoring client 부분만 placeholder로 대체한다.

## 안정성 확인

각 방안 폴더의 `results/` 아래에는 세 파일이 생성된다.

| 파일 | 의미 |
| --- | --- |
| `mbti_score_changes.csv` | 실행별 최종 MBTI와 축별 점수 변화 원본 로그 |
| `stability_summary.csv` | 반복 실행 결과의 안정성 요약 |
| `STABILITY_REPORT.md` | 사람이 읽기 쉬운 축별 안정성 리포트 |

전체 비교는 아래 문서에서 한눈에 본다.

```text
test/jaewung/mbti_scoring_experiments/STABILITY_DASHBOARD.md
```

기존 프로세스의 페르소나 점수화 파일을 이용해 `persona_direct`만 실제 LLM으로 실행하려면 아래 옵션을 사용한다.

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py --use-persona-llm
```

이 옵션은 `app/backend/mbti/services/persona.py`, `response_scoring.py`, `llm_config.py`를 import하고 기존 `LangChainMbtiScoringClient`를 사용한다. 외부 LLM API를 호출할 수 있으므로 비용과 API 키 설정을 확인한 뒤 수동으로 실행한다.

루브릭코드 방식은 전용 프롬프트를 사용한다. LLM은 점수를 직접 만들지 않고, `docs/한재웅/datasets/mbti_scoring_rubrics.v1.json`에서 해당 축에 허용된 `rubric_code` 중 하나만 반환한다. 실험 코드는 반환된 `rubric_code`를 검증한 뒤 루브릭 파일의 고정 `score`와 `status`로 변환한다.

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py --use-rubric-llm
```

루브릭코드 프롬프트의 핵심 제약은 아래와 같다.

```text
- target_axis 하나만 판단한다.
- allowed_rubrics 목록에 있는 rubric_code 하나만 선택한다.
- score, status, letter, direction은 절대 반환하지 않는다.
- decision_rule_ko를 1순위 기준으로 사용한다.
- signals_ko는 예시로만 사용한다.
- 축 근거가 있으면 가장 가까운 STRONG/WEAK/MIXED 코드를 고른다.
- 일시 조건이면 EXCLUDE_CONTEXTUAL, 근거 부족이면 EXCLUDE_INSUFFICIENT를 고른다.
```

## 다음 작업

1. 후보별 프롬프트와 출력 스키마 확정
2. `persona_direct`와 `rubric_code` 실험 결과를 확인한 뒤 나머지 placeholder 로직을 실제 LLM 호출 또는 저장된 LLM 응답 재생 방식으로 교체
3. 같은 샘플셋을 여러 번 반복 실행해 재현성 측정
4. 결과가 가장 안정적인 방식을 운영 `response_scoring.py` 또는 그 주변 scoring client로 승격
## Single-model candidate ranking

For the first round, test one model at a time. The goal is not to prove one model is always best, but to find a practical service candidate with good stability, low friction, and acceptable cost.

| Rank | Combo | Provider | Model | Why test it first |
| --- | --- | --- | --- | --- |
| 1 | `single_1_openai_baseline` | `openai` | `gpt-5.4-mini` | OpenAI is the primary supported provider, so this is the service baseline. |
| 2 | `single_2_openai_quality` | `openai` | `gpt-5.4` | Higher-quality OpenAI comparison candidate. |
| 3 | `single_3_groq_qwen` | `groq` | `qwen/qwen3-32b` | Non-OpenAI comparison candidate after excluding Gemini and Groq Llama. |

Recommended `app/backend/.env` shape:

```env
OPENAI_API_KEY=...
GROQ_API_KEY=...
GROQ_BASE_URL=https://api.groq.com/openai/v1

MBTI_SCORING_PROVIDER=openai
MBTI_SCORING_MODEL=gpt-5.4-mini

MBTI_SINGLE_1_PROVIDER=openai
MBTI_SINGLE_1_MODEL=gpt-5.4-mini

MBTI_SINGLE_2_PROVIDER=openai
MBTI_SINGLE_2_MODEL=gpt-5.4

MBTI_SINGLE_3_PROVIDER=groq
MBTI_SINGLE_3_MODEL=qwen/qwen3-32b
```

Example runs:

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py --strategy persona_direct --use-persona-llm --combo single_1_openai_baseline
python test\jaewung\mbti_scoring_experiments\run_experiment.py --strategy persona_direct --use-persona-llm --combo single_2_openai_quality
python test\jaewung\mbti_scoring_experiments\run_experiment.py --strategy persona_direct --use-persona-llm --combo single_3_groq_qwen
```

The result CSV records `experiment_combo`, `provider`, `model`, and `model_label`, so repeated runs can be grouped by the exact model used.

## Current experiment groups

```text
mbti_scoring_experiments/
  single_llm/
    01_persona_direct/
    02_rubric_code/
  multi_llm/
    03_triple_majority/
    04_hundred_point_ensemble/
    05_triple_supervisor/
```

For the first single-LLM round, use this control/experiment matrix.

| Group | Strategy | Combo | Meaning |
| --- | --- | --- | --- |
| control | `persona_direct` | `single_1_openai_baseline` | Current-service-like persona scoring with the OpenAI baseline. |
| experiment | `persona_direct` | `single_2_openai_quality` | Same scoring method, higher-quality OpenAI model comparison. |
| experiment | `persona_direct` | `single_3_groq_qwen` | Same scoring method, Groq Qwen model comparison. |
| experiment | `rubric_code` | `single_1_openai_baseline` | Same OpenAI baseline, rubric-code scoring comparison. |
| experiment | `rubric_code` | `single_2_openai_quality` | Rubric-code scoring with the higher-quality OpenAI model. |
| experiment | `rubric_code` | `single_3_groq_qwen` | Rubric-code scoring with Groq Qwen. |

The result CSV records `experiment_family`, `experiment_group`, and `experiment_variable` so the control and experiment runs can be filtered directly.
