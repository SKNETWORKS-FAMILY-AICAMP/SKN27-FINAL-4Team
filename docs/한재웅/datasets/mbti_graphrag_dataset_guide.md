# MBTI Graph RAG 데이터셋 사용 가이드

## 목적

이 데이터셋은 근거리포트 문장을 직접 저장하지 않는다. 대신 16Personalities의 Big Five 계열 성격 설명 구조를 바탕으로, LLM이 사용자의 월간 MBTI 결과와 축별 점수 근거를 함께 참고해 자연스러운 설명을 구성할 수 있도록 한다.

## 파일 구성

| 파일 | 역할 |
| --- | --- |
| `mbti_graphrag_nodes.csv` | aspect, trait, role, type 노드 정의 |
| `mbti_graphrag_edges.csv` | aspect-trait, role-trait, type-role 관계 |
| `mbti_graphrag_type_traits.csv` | 16개 유형별 4개 성격 축 매핑 |
| `mbti_graphrag_fact_atoms.csv` | 유형별 핵심 성향, 강점, 주의점 fact |
| `mbti_graphrag_everyday_atoms.csv` | 일상 행동, 대화 방식, 선택 방식 fact |

## 검색 권장 방식

1. `estimated_mbti_type`으로 `type_node_id`를 찾는다.
2. `mbti_graphrag_type_traits.csv`에서 해당 유형의 trait 조합을 가져온다.
3. `mbti_graphrag_edges.csv`로 role과 trait 관계를 확장한다.
4. `mbti_graphrag_fact_atoms.csv`에서 핵심 성향, 강점, 주의점을 검색한다.
5. `mbti_graphrag_everyday_atoms.csv`에서 일상적 설명 후보를 검색한다.
6. LLM은 검색 결과를 원문처럼 붙이지 않고, 사용자 Q&A 근거와 함께 새 문장으로 요약한다.

## 리포트 생성 시 주의

- `knowledge_text`, `fact_text`, `everyday_fact`를 그대로 복사하지 않는다.
- 사용자 답변 근거가 없는 성향은 단정하지 않는다.
- “당신은 원래 이런 사람”이 아니라 “이번 달 답변에서는 이런 경향이 관찰됨”으로 표현한다.
- `avoid_expression`에 들어 있는 표현은 리포트에 사용하지 않는다.
- 16Personalities의 유형 설명은 참고 지식이며, 공식 심리 진단처럼 표현하지 않는다.

## 예시 조합

INTP가 산출된 경우:

- type trait: Introverted, Intuitive, Thinking, Prospecting
- role: Analysts
- fact atoms: 원리 탐색, 논리적 검토, 실행 지연 주의
- everyday atoms: 궁금한 주제를 깊게 파고듦, 질문으로 논리를 확인함, 여러 가능성을 열어둠

LLM은 위 정보를 사용자 실제 답변 근거와 함께 섞어, “관심 주제의 원리를 탐색하려는 답변이 반복되었다”처럼 새 문장을 구성한다.
