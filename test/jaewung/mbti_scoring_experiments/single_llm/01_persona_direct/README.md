# 01 Persona Direct

페르소나 기반 직접 채점 방식이다.

기존 MBTI 분석가 페르소나 프롬프트를 사용해 LLM이 응답별 점수를 직접 반환한다. 실험 실행은 backend의 실제 `run_monthly_mbti_pipeline()`에 이 scoring client를 끼워 넣는 방식이다.

```text
answer
→ persona prompt
→ score/status/reason
→ backend monthly pipeline
→ results/mbti_score_changes.csv
```

## 실행

기본 실행은 외부 API를 호출하지 않는 placeholder다.

```powershell
python test\jaewung\mbti_scoring_experiments\01_persona_direct\run.py
```

기존 프로세스의 LLM 점수화 파일을 이용하려면 `--use-llm`을 붙인다.

```powershell
python test\jaewung\mbti_scoring_experiments\01_persona_direct\run.py --use-llm
```

결과는 이 폴더의 `results/mbti_score_changes.csv`에 실행별로 누적 저장된다.
