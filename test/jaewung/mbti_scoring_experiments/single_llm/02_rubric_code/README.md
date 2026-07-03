# 02 Rubric Code

루브릭코드 기반 채점 방식이다.

LLM은 점수를 직접 만들지 않고, 해당 축에 허용된 `rubric_code` 하나만 선택한다. 실험 코드는 `docs/한재웅/datasets/mbti_scoring_rubrics.v1.json`의 고정 매핑으로 `score/status`를 변환한다.

상세 프로세스는 [PROCESS_FLOW.md](./PROCESS_FLOW.md)에 정리한다.

이 방안은 바뀌는 최소 모듈만 이 폴더 안으로 복사해 개조한다.

```text
pipeline/response_scoring.py
```

나머지 월간 파이프라인, 그래프 점수 계산, 최종 MBTI 조합은 backend 원본 모듈을 import해서 연결한다.

```text
answer + allowed_rubrics
→ rubric_code-only prompt
→ rubric_code
→ server-side score/status mapping
→ backend monthly pipeline
→ results/mbti_score_changes.csv
```

## 실행

기본 실행은 외부 API를 호출하지 않는 placeholder다.

```powershell
python test\jaewung\mbti_scoring_experiments\02_rubric_code\run.py
```

이 placeholder도 별도 코드/점수 매핑을 하드코딩하지 않는다. `mbti_scoring_rubrics.v1.json`의 `rubric_code`, `signals_ko`, `decision_rule_ko`, `score`, `status`를 읽어서 dry-run용으로만 가장 가까운 코드를 고른다.

루브릭코드 전용 프롬프트로 LLM을 호출하려면 `--use-llm`을 붙인다.

```powershell
python test\jaewung\mbti_scoring_experiments\02_rubric_code\run.py --use-llm
```

결과는 이 폴더의 `results/mbti_score_changes.csv`에 실행별로 누적 저장된다.
