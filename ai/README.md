# ai/ — AI 모델 및 에이전트 작업 공간

LangGraph 멀티에이전트 오케스트레이션, KcELECTRA 감정분류 모델, 심리척도 추정 파이프라인이 위치합니다.

## 폴더 구조

| 폴더/파일 | 역할 |
|---|---|
| `agents/` | LangGraph 멀티에이전트 — 노드(nodes.py), 페르소나(personas.py), 상태(state.py), LLM 설정(llm.py), MBTI 질문(mbti.py), 웹 에이전트(web_agent.py) |
| `emotion/` | KcELECTRA + XGBoost 감정분류 파이프라인 — 학습·추론·산출물(artifacts/) |
| `experiments/` | 감정분류 개선 실험 노트북 및 결과 기록 |
| `scale/` | 6종 임상 척도(PHQ-9, GAD-7 등) 간접 추정 모듈 |
