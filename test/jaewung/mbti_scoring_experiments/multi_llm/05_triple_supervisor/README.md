# 05 Triple Supervisor

3개 LLM 점수 산정 + 규칙 기반 슈퍼바이저 방식이다.

기존 서비스의 페르소나 직접 점수 산정 프롬프트를 실험 폴더 안의
`pipeline/response_scoring.py`에 복사해 두고, 같은 응답을 세 LLM Judge가
독립적으로 점수화한다. 이후 슈퍼바이저는 LLM을 다시 호출하지 않고 코드 규칙으로
최종 점수를 고른다.

```text
answer
-> LLM A score/status/reason
-> LLM B score/status/reason
-> LLM C score/status/reason
-> supervisor rule
   - coded 점수가 2개 이상이고 같은 점수가 있으면 최빈값
   - coded 점수가 2개 이상인데 모두 다르면 중앙값
   - coded 점수가 1개 이하이면 insufficient_context 또는 failed
-> backend monthly pipeline
-> results/mbti_score_changes_persona_prompt_unified_no_random_20260704.csv
-> results/stability_summary_persona_prompt_unified_no_random_20260704.csv
-> results/STABILITY_REPORT_persona_prompt_unified_no_random_20260704.md
```

## 실행

API를 호출하지 않는 placeholder 실행:

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py --strategy triple_supervisor
```

실제 3개 LLM Judge를 호출하는 실행:

```powershell
python test\jaewung\mbti_scoring_experiments\run_experiment.py --strategy triple_supervisor --use-triple-supervisor-llm
```

하위 폴더 실행 스크립트로도 동일하게 실행할 수 있다.

```powershell
python test\jaewung\mbti_scoring_experiments\multi_llm\05_triple_supervisor\run.py --use-llm
```

기본값은 공통 `--provider`, `--model` 또는 환경변수의 단일 모델을 세 Judge에 모두 사용한다.
Judge별 모델을 다르게 쓰려면 아래 환경변수를 지정한다.

```env
MBTI_JUDGE_1_PROVIDER=openai
MBTI_JUDGE_1_MODEL=gpt-5.4-mini
MBTI_JUDGE_2_PROVIDER=groq
MBTI_JUDGE_2_MODEL=qwen/qwen3-32b
MBTI_JUDGE_3_PROVIDER=openai
MBTI_JUDGE_3_MODEL=gpt-5.4-mini
```

결과는 `results/` 아래 새 기준 전용 CSV와 안정성 리포트로 누적된다. 기존 구 실험 파일인
`mbti_score_changes.csv`와 섞지 않는다.

다른 이름의 독립 결과 세트를 만들고 싶으면 아래 환경변수를 지정한다.

```env
MBTI_EXPERIMENT_RESULT_SET=my_clean_run_20260704
```
