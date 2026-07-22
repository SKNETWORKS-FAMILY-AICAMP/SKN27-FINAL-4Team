# 04 Hundred Point Ensemble

100점제 앙상블 구간 다수결/정규화 평균 방식이다.

3개 LLM이 0~100점으로 응답을 판단하고, 점수를 5개 성향 구간으로 변환한 뒤 구간 다수결과 정규화 평균으로 최종 점수를 정하는 실험 방식이다.

```text
answer
→ three 0-100 scores
→ five-level bucket vote
→ normalized score
→ backend monthly pipeline
→ results/mbti_score_changes.csv
```

## 실행

현재는 외부 API를 호출하지 않는 placeholder다.

```powershell
python test\jaewung\mbti_scoring_experiments\04_hundred_point_ensemble\run.py
```

결과는 이 폴더의 `results/mbti_score_changes.csv`에 실행별로 누적 저장된다.
