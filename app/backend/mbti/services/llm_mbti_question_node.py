from __future__ import annotations

import os
from random import Random
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from mbti.services.mbti_question_node import MbtiAxis, build_chatbot_response_payload


MBTI_AXES: tuple[MbtiAxis, ...] = ("IE", "SN", "TF", "JP")

AXIS_GUIDES: dict[MbtiAxis, str] = {
    "IE": """ E(Extraverted): 외향이 강한 사람은 에너지가 주로 사람과의 상호작용, 외부 활동, 대화, 자극적인 환경에서 생깁니다.

    생각 방식: 혼자 오래 생각하기보다 말하거나 행동하면서 생각이 정리된다.
    대화 태도: 즉각적으로 반응하고, 자신의 생각을 비교적 빠르게 밖으로 표현한다.
    에너지 회복: 사람을 만나거나 활동적인 환경에 있을 때 활력이 생긴다.
    관심 방향: 자신의 내면보다 외부 사건, 사람들, 분위기, 활동에 관심이 간다.
    행동 방식: 생각이 완전히 정리되지 않아도 일단 시도하거나 말해보는 편이다.
    관계 방식: 다양한 사람과 폭넓게 교류하는 것을 선호한다.
    스트레스 반응: 혼자 오래 있거나 자극이 부족하면 답답함, 무기력함을 느끼기 쉽다.
    가늠 기준: 대화와 활동 후 더 살아나는 사람이라면 E 성향이 강할 가능성이 높다.
    

I(Introverted): 내향이 강한 사람에너지가 주로 혼자 있는 시간, 생각, 내적 정리, 깊은 집중에서 생깁니다.

    생각 방식: 먼저 혼자 생각한 뒤 말하는 것을 선호한다.
    대화 태도: 즉답보다 시간을 갖고 정리해서 말하려 한다.
    에너지 회복: 사람을 많이 만나면 피로가 쌓이고, 혼자 있어야 회복된다.
    관심 방향: 외부 사건보다 자신의 생각, 의미, 감정 정리에 집중한다.
    행동 방식: 충분히 생각하고 준비한 뒤 움직이려 한다.
    관계 방식: 넓은 관계보다 깊고 안정적인 관계를 선호한다.
    스트레스 반응: 갑작스러운 만남, 과도한 소통, 시끄러운 환경에서 쉽게 지친다.
    가늠 기준: 혼자 있을 때 정신이 정리되고 에너지가 회복된다면 I 성향이 강할 가능성이 높다.
""",
    "SN": """SN:정보 인식 방식
- S(Sensing):감각이 강한 사람은 정보를 받아들일 때 현실, 경험, 구체적 사실, 실제로 확인 가능한 것을 중시합니다.

    생각 방식: 추상적 가능성보다 실제 사례와 경험을 기준으로 판단한다.
    대화 태도: 구체적인 근거, 수치, 절차, 예시가 있어야 납득한다.
    에너지 회복: 불확실한 상상보다 현실적으로 해결 가능한 일에 집중할 때 안정감을 느낀다.
    관심 방향: 미래의 가능성보다 현재 상황, 실제 문제, 당장 필요한 것에 관심이 간다.
    행동 방식: 검증된 방법, 익숙한 절차, 실용적인 방식을 선호한다.
    관계 방식: 말보다 행동, 약속 이행, 현실적 도움을 중요하게 본다.
    스트레스 반응: 말이 너무 추상적이거나 현실성이 부족하면 답답함을 느낀다.
    가늠 기준: “그래서 실제로 어떻게 되는가?”를 자주 따진다면 S 성향이 강할 가능성이 높다.

- N(iNtuitive):직관이 강한 사람은 정보를 받아들일 때 가능성, 의미, 패턴, 미래 방향, 숨은 연결성을 중시합니다.

    생각 방식: 눈앞의 사실보다 그 사실이 의미하는 흐름과 가능성을 먼저 본다.
    대화 태도: 비유, 개념, 가설, 큰 그림 중심의 대화를 선호한다.
    에너지 회복: 새로운 아이디어, 상상, 전략, 변화 가능성을 생각할 때 흥미가 생긴다.
    관심 방향: 현재의 구체적 사실보다 미래, 의미, 구조, 가능성에 관심이 간다.
    행동 방식: 기존 방식보다 더 새롭거나 더 나은 방식을 찾으려 한다.
    관계 방식: 단순한 일상 대화보다 깊은 의미, 가치관, 세계관을 나누는 관계를 선호한다.
    스트레스 반응: 반복적이고 세부적인 현실 업무만 계속되면 지루함을 느끼기 쉽다.
    가늠 기준: “이게 앞으로 무엇을 의미하는가?”를 자주 생각한다면 N 성향이 강할 가능성이 높다.
""",
    "TF": """T(Thinking): 사고가 강한 사람은 판단할 때 논리, 객관성, 효율, 원칙, 일관성을 중시합니다.

    생각 방식: 감정보다 원인, 구조, 논리적 타당성을 먼저 따진다.
    대화 태도: 공감 표현보다 문제 분석과 해결책 제시가 먼저 나온다.
    에너지 회복: 감정적으로 얽힌 상황보다 기준이 명확하고 합리적인 상황에서 편안함을 느낀다.
    관심 방향: 누가 기분 나쁜지보다 무엇이 맞고 틀린지, 무엇이 효율적인지에 집중한다.
    행동 방식: 필요하다면 불편한 말이나 비판도 직접적으로 할 수 있다.
    관계 방식: 상대를 배려하더라도 진실성, 정확성, 합리성을 중요하게 본다.
    스트레스 반응: 비논리적 주장, 감정적 압박, 비효율적인 의사결정에 답답함을 느낀다.
    가늠 기준: 갈등 상황에서 먼저 “무엇이 맞는가?”를 따진다면 T 성향이 강할 가능성이 높다.

- F(Feeling): 감정이 강한 사람은 판단할 때 사람의 감정, 관계, 가치, 조화, 맥락을 중시합니다.

    생각 방식: 논리적 결론뿐 아니라 그 결정이 사람에게 미칠 영향을 함께 고려한다.
    대화 태도: 상대의 감정, 말투, 분위기 변화를 민감하게 읽는다.
    에너지 회복: 따뜻한 인정, 공감, 정서적 연결이 있을 때 안정감을 느낀다.
    관심 방향: 무엇이 맞는가뿐 아니라 누가 상처받는지, 관계가 어떻게 되는지에 집중한다.
    행동 방식: 직접적인 비판보다 완곡한 표현이나 배려 있는 전달을 선호한다.
    관계 방식: 정서적 신뢰, 진심, 배려, 따뜻한 교류를 중요하게 본다.
    스트레스 반응: 차가운 말투, 무시당하는 느낌, 관계 갈등에 크게 영향을 받는다.
    가늠 기준: 갈등 상황에서 먼저 “사람들이 어떻게 느낄까?”를 생각한다면 F 성향이 강할 가능성이 높다. """,
    "JP": """J(Judgment): 판단이 강한 사람은 생활과 일을 처리할 때 계획, 정리, 확정, 마감, 예측 가능성을 선호합니다.
            

    생각 방식: 열린 가능성을 오래 두기보다 빠르게 정리하고 결론을 내리려 한다.
    대화 태도: 불명확한 이야기보다 일정, 기준, 역할, 결론이 분명한 대화를 선호한다.
    에너지 회복: 계획이 세워지고 일이 정리되어 있을 때 안정감을 느낀다.
    관심 방향: 지금 무엇을 정해야 하는지, 어떤 순서로 처리해야 하는지에 집중한다.
    행동 방식: 미리 준비하고, 마감 전에 끝내고, 계획대로 진행하려 한다.
    관계 방식: 약속, 시간, 책임, 예측 가능한 태도를 중요하게 본다.
    스트레스 반응: 갑작스러운 변경, 미정 상태, 지연, 무계획에 스트레스를 받는다.
    가늠 기준: 일이 확정되고 정리되어야 마음이 놓인다면 J 성향이 강할 가능성이 높다.

- P(Prospecting / Perceiving):인식이 강한 사람은 생활과 일을 처리할 때 유연성, 즉흥성, 선택지, 상황 적응을 선호합니다.

    생각 방식: 결론을 빨리 내리기보다 상황을 더 보고 가능성을 열어두려 한다.
    대화 태도: 확정적인 말보다 “일단 해보고 보자”, “상황 봐서 정하자”는 식의 표현을 자주 쓴다.
    에너지 회복: 자유롭게 조정할 수 있고 선택지가 열려 있을 때 편안함을 느낀다.
    관심 방향: 정해진 계획보다 그때그때 생기는 기회와 변화에 관심이 간다.
    행동 방식: 계획대로 밀고 가기보다 상황에 맞춰 유연하게 바꾸려 한다.
    관계 방식: 지나치게 통제적이거나 빡빡한 관계보다 자유롭고 여유 있는 관계를 선호한다.
    스트레스 반응: 너무 이른 확정, 과도한 규칙, 빡빡한 일정에 답답함을 느낀다.
    가늠 기준: 선택지가 열려 있어야 마음이 편하다면 P 성향이 강할 가능성이 높다.""",
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
- 최근의 경향을 물어야한다.
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


def build_mbti_period_key(reference_at: Any | None = None) -> str:
    """Return the monthly period key used by MBTI Q&A persistence."""
    from django.utils import timezone

    value = reference_at or timezone.now()
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())

    return timezone.localtime(value).strftime("%Y-%m")


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
