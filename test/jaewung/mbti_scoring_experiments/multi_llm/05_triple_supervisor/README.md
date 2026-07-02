# 05 Triple Supervisor

3자 LLM 슈퍼바이저 방식이다.

3개 LLM의 응답별 판단과 근거를 모은 뒤, 규칙 기반 슈퍼바이저가 최종 응답 점수를 확정하는 실험 방식이다.

```text
answer
→ LLM A judgment
→ LLM B judgment
→ LLM C judgment
→ supervisor rule
→ backend monthly pipeline
→ results/mbti_score_changes.csv
```

## 실행

현재는 외부 API를 호출하지 않는 placeholder다.

```powershell
python test\jaewung\mbti_scoring_experiments\05_triple_supervisor\run.py
```

결과는 이 폴더의 `results/mbti_score_changes.csv`에 실행별로 누적 저장된다.
