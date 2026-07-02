from __future__ import annotations

import os
from random import Random
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from mbti.services.mbti_question_node import MbtiAxis, build_chatbot_response_payload


MBTI_AXES: tuple[MbtiAxis, ...] = ("IE", "SN", "TF", "JP")

AXIS_GUIDES: dict[MbtiAxis, str] = {
    "IE": "외향-내향 지표는 심리적 에너지와 관심의 방향이 자신의 내부와 외부 중 주로 어느 쪽으로 향하느냐를 보여 주는 지표이다. ",
    "SN": "감각-직관 지표는 사람이나 사물 등의 대상을 인식하고 지각하는 방식에서 감각과 직관 중 어느 쪽을 주로 더 사용하는지에 관한 지표이다.",
    "TF": "사고-감정 지표는 수집한 정보를 바탕으로 판단하고 결정을 내릴 때 사고와 감정 중 어떤 것을 더 선호하는지 알려 준다. ",
    "JP": "판단-인식 지표는 인식 기능과 판단 기능을 바탕으로 실생활에 대처하는 방식에 있어 판단과 인식 중 어느 쪽을 주로 선호하는지에 관한 경향성을 나타내는 지표이다.",
}

DEFAULT_LLM_QUESTION_MODEL = "gpt-5.4-mini"
DEFAULT_LLM_QUESTION_TEMPERATURE = 0.9
DEFAULT_LLM_QUESTION_MAX_TOKENS = 120
MAX_CONTEXT_MESSAGES = 8


LLM_MBTI_QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
너는 웰니스 챗봇 대화 중 MBTI 성향을 자연스럽게 파악하기 위한 질문을 만드는 역할이다.

반드시 지킬 조건:
- 질문은 딱 1개만 만든다.
- 목표 축 하나만 측정한다.
- MBTI, 성격검사, 유형, I/E, S/N, T/F, J/P 같은 표현을 직접 쓰지 않는다.
- 사용자가 최근 경험을 바탕으로 말할수있게 묻는다.
- 예/아니오로만 답하게 만들지 않는다.
- 너무 검사 문항처럼 딱딱하게 쓰지 않는다.
- 한 문장 또는 두 문장 이내로 작성한다.
- 따옴표, 번호, 설명, 접두어 없이 질문 문장만 출력한다.
- 친근한 반말 말투로 질문한다.
- 16 personalities 같은 big5계열 검사의 질문과 유사한 질문이어야한다.
- 대답을 분석했을때 정도가 나올수있는 질문을 해야한다.(즉 다시말해서 이분법으로 질문하더라도 단정적인 대답이 나오면 안된다.)
- 질문이 너무 길어도 않된다. 적당한 길이여야한다.
- 적절한 길이로 대답할수있어야한다.
- 너무 심오한 질문말고 일상적인 상황,생각,사고를 기반으로 질문해야한다.
""",
        ),
        (
            "human",
            """
목표 축: {axis}
축 설명: {axis_guide}

최근 대화:
{conversation_context}

위 대화 흐름에 어색하지 않게 이어질 수 있는 질문을 하나 만들어라.
""",
        ),
    ]
)


def select_random_mbti_axis(*, seed: int | None = None) -> MbtiAxis:
    return Random(seed).choice(MBTI_AXES)


def build_session_context(session: Any | None, *, limit: int = MAX_CONTEXT_MESSAGES) -> str:
    if session is None:
        return "아직 저장된 대화가 없다."
        
    messages = list(session.messages.order_by("-created_at")[:limit])
    messages.reverse()

    if not messages:
        return "아직 저장된 대화가 없다."

    lines: list[str] = []
    for message in messages:
        speaker = "사용자" if message.role == "user" else "챗봇"
        lines.append(f"{speaker}: {message.content}")
    return "\n".join(lines)


def build_default_question_llm() -> Any:
    from langchain_openai import ChatOpenAI

    model = (
        os.getenv("MBTI_QUESTION_MODEL")
        or os.getenv("OPENAI_MODEL")
        or DEFAULT_LLM_QUESTION_MODEL
    )
    temperature = float(os.getenv("MBTI_QUESTION_TEMPERATURE", DEFAULT_LLM_QUESTION_TEMPERATURE))
    max_tokens = int(os.getenv("MBTI_QUESTION_MAX_TOKENS", DEFAULT_LLM_QUESTION_MAX_TOKENS))

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def clean_generated_question(text: str) -> str:
    question = text.strip()
    question = question.removeprefix("-").strip()
    question = question.strip("\"'“”‘’")

    if "\n" in question:
        question = next((line.strip() for line in question.splitlines() if line.strip()), question)

    return question


def generate_random_axis_mbti_question(
    session: Any | None,
    *,
    axis: MbtiAxis | None = None,
    seed: int | None = None,
    llm: Any | None = None,
) -> dict[str, Any]:
    selected_axis = axis or select_random_mbti_axis(seed=seed)
    conversation_context = build_session_context(session)
    question_llm = llm or build_default_question_llm()
    chain = LLM_MBTI_QUESTION_PROMPT | question_llm | StrOutputParser()

    text = chain.invoke(
        {
            "axis": selected_axis,
            "axis_guide": AXIS_GUIDES[selected_axis],
            "conversation_context": conversation_context,
        }
    )
    question_text = clean_generated_question(text)

    if not question_text:
        raise ValueError("LLM did not generate an MBTI question.")

    return {
        "id": None,
        "axis": selected_axis,
        "text": question_text,
        "source": "llm_generated",
    }


def ask_llm_random_mbti_question_for_session(
    session: Any,
    *,
    seed: int | None = None,
    llm: Any | None = None,
    persist: bool | None = None,
) -> dict[str, Any]:
    """Generate one random-axis MBTI question with LangChain for this chat session.

    Input: ChatSession instance.
    Output: existing chatbot message payload plus MBTI metadata.
    """
    question = generate_random_axis_mbti_question(
        session,
        seed=seed,
        llm=llm,
    )
    should_persist = not getattr(session, "is_secret", False) if persist is None else persist

    if not should_persist:
        return {
            "id": None,
            "role": "assistant",
            "content": question["text"],
            "emotion_label": None,
            "created_at": None,
            "mbti_question": question,
            "mbti_question_completed": False,
        }

    from chat.models import ChatMessage

    message = ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=question["text"],
    )

    return build_chatbot_response_payload(
        message=message,
        question=question,
        completed=False,
    )
