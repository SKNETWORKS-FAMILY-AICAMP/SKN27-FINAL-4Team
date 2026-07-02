# 타로카드 문장형 해석 데이터 / RAG 사용 가이드

## 생성 목적

기존 CSV의 `upright_meaning`, `reversed_meaning`, `love_meaning`, `career_meaning` 컬럼은 키워드 중심입니다.
LLM이 자연스러운 조언을 생성하려면 카드 의미를 문장 단위로 제공하는 편이 안정적이므로, 아래 컬럼을 추가한 확장 CSV를 생성했습니다.

## 생성 파일

- `tarot_card_sentence_meanings_ko.csv`: 기존 78장 카드 데이터 + 한국어 문장형 해석 컬럼
- `tarot_card_rag_chunks_ko.jsonl`: RAG 검색/임베딩용 chunk 데이터

## 추가된 CSV 컬럼

| 컬럼명 | 설명 |
|---|---|
| `upright_meaning_sentence_ko` | 정방향 일반 해석을 문장형으로 확장 |
| `reversed_meaning_sentence_ko` | 역방향 일반 해석을 문장형으로 확장 |
| `love_meaning_sentence_ko` | 연애 주제 해석을 문장형으로 확장 |
| `career_meaning_sentence_ko` | 진로/일 주제 해석을 문장형으로 확장 |
| `advice_seed_ko` | LLM이 조언을 생성할 때 참고할 핵심 조언 문장 |
| `llm_context_ko` | RAG 또는 프롬프트에 그대로 넣기 쉬운 카드별 통합 컨텍스트 |

## 추천 RAG 흐름

1. 사용자가 질문과 주제를 입력합니다.
2. 백엔드에서 카드 3장을 뽑고 각 카드의 방향을 결정합니다.
3. 뽑힌 카드명 + 방향 + 주제를 기준으로 `tarot_card_rag_chunks_ko.jsonl` 또는 DB에서 관련 chunk를 검색합니다.
4. 검색된 chunk를 LLM 프롬프트의 근거 문맥으로 넣습니다.
5. LLM은 다음 구조로 답변합니다.

```txt
- 전체 흐름
- 현재 상황 카드 해석
- 숨은 흐름 카드 해석
- 조언 카드 해석
- 현실적인 조언 2~3개
- 한 줄 메시지
- 참고용 안내 문구
```

## 프롬프트 예시

```txt
너는 사용자의 질문에 대해 타로카드 3장 리딩을 제공하는 조언 생성기다.
아래 카드 해석 컨텍스트만 근거로 사용해라.
결론을 단정하지 말고, 사용자가 스스로 상황을 돌아볼 수 있도록 부드럽게 조언해라.

[사용자 질문]
{question}

[주제]
{topic}

[뽑힌 카드]
1. 현재 상황: {card_1_name} / {card_1_orientation}
2. 숨은 흐름: {card_2_name} / {card_2_orientation}
3. 조언: {card_3_name} / {card_3_orientation}

[검색된 카드 해석 컨텍스트]
{retrieved_context}

[응답 형식]
### 전체 흐름
### 카드별 해석
### 지금 필요한 조언
### 한 줄 메시지
### 참고 안내
```

## 데이터 개수

- 카드 수: 78
- RAG chunk 수: 390

