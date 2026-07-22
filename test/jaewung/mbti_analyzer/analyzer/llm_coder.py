from __future__ import annotations

import os
from typing import Protocol

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from test.jaewung.mbti_analyzer.analyzer.schemas import LocalContextWindow, MessageCodingResult


class MbtiCoder(Protocol):
    def code(self, window: LocalContextWindow) -> MessageCodingResult:
        ...


class LangChainOpenAIMbtiCoder:
    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0,
    ) -> None:
        load_dotenv()

        model_name = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
        )

        structured_llm = llm.with_structured_output(MessageCodingResult)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
당신은 MBTI 유형을 직접 판정하는 모델이 아니다.
당신의 역할은 사용자 발화를 MBTI 4축 taxonomy에 맞는 근거 단위로 코딩하는 것이다.

반드시 지킬 규칙:
1. estimated_type, MBTI 유형명, 성격 단정 문구를 출력하지 않는다.
2. 입력 맥락에서 명확한 근거가 있을 때만 axis_evidence를 생성한다.
3. 근거가 부족하면 coding_status를 insufficient_context로 둔다.
4. evidence_span은 반드시 입력 context_text 안에 존재하는 문장 또는 구절이어야 한다.
5. normalized_keyword는 원문 단어 복사가 아니라 맥락 기반 정규화 키워드로 작성한다.
6. 하나의 발화에서 여러 축 근거가 명확하면 여러 axis_evidence를 만들 수 있다.
7. 과잉해석하지 않는다.

사용 가능한 taxonomy:

IE:
- I: 혼자 회복, 조용한 환경 선호, 깊은 대화 선호, 사회적 피로, 생각 정리 후 말함
- E: 사람과 에너지, 모임 선호, 말하면서 정리, 외부 활동 선호, 즉시 대화

SN:
- S: 구체적 사실, 실제 경험, 현실 조건, 세부 정보, 현재 가능한 선택
- N: 가능성 탐색, 의미 해석, 패턴 발견, 미래 시나리오, 추상적 연결

TF:
- T: 논리 기준, 효율, 원인 분석, 객관 판단, 일관성, 원칙
- F: 감정 고려, 관계 영향, 공감, 배려, 상처/위로, 가치 판단

JP:
- J: 계획, 확정, 마감, 정리, 통제감, 먼저 결정
- P: 유연함, 즉흥, 선택지 유지, 변화 가능성, 상황 대응, 미루기
""",
                ),
                (
                    "human",
                    """
message_id: {message_id}

분석 대상 사용자 발화:
{target_user_text}

Local Context Window:
{context_text}
""",
                ),
            ]
        )

        self.chain = prompt | structured_llm

    def code(self, window: LocalContextWindow) -> MessageCodingResult:
        result = self.chain.invoke(
            {
                "message_id": window.target_message_id,
                "target_user_text": window.target_user_text,
                "context_text": window.context_text,
            }
        )

        if isinstance(result, MessageCodingResult):
            return result

        return MessageCodingResult.model_validate(result)