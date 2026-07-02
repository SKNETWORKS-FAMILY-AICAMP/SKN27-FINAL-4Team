# 03 Triple Majority

3자 LLM 다수결 방식이다.

3개 LLM이 같은 응답을 기존 점수 체계로 각각 판단하고, 2개 이상 일치한 점수를 최종 응답 점수로 확정하는 실험 방식이다.

```text
answer
→ LLM A score
→ LLM B score
→ LLM C score
→ majority vote
→ backend monthly pipeline
→ results/mbti_score_changes.csv
```

## 실행

현재는 외부 API를 호출하지 않는 placeholder다.

```powershell
python test\jaewung\mbti_scoring_experiments\03_triple_majority\run.py
```

결과는 이 폴더의 `results/mbti_score_changes.csv`에 실행별로 누적 저장된다.
