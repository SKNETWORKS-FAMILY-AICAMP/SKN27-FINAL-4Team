from __future__ import annotations

from dataclasses import asdict, dataclass
from random import Random
from typing import Any, Literal


MbtiAxis = Literal["IE", "SN", "TF", "JP"]


@dataclass(frozen=True)
class MbtiQuestion:
    id: int
    axis: MbtiAxis
    text: str


MBTI_AXIS_QUESTIONS: tuple[MbtiQuestion, ...] = (
    MbtiQuestion(1, "IE", "말하다 보니 생각난 건데, 최근에 기운이 좀 돌아왔다 싶었던 순간은 어떤 장면이었어?"),
    MbtiQuestion(2, "IE", "아까 얘기랑은 살짝 다른데, 지친 날 끝에 자연스럽게 찾게 되는 건 뭐였어?"),
    MbtiQuestion(3, "IE", "쉬는 틈이 생기면 사람마다 손이 가는 게 다르잖아, 너는 최근에 어디로 손이 갔어?"),
    MbtiQuestion(4, "IE", "생각이 엉킨 날엔 그냥 넘기기 어렵던데, 그럴 때 요새는 어떻게 풀렸어?"),
    MbtiQuestion(5, "IE", "좋은 일이 있었을 때 그 기분을 가만히 두는 사람도 있고 나누는 사람도 있잖아, 너는 최근에 어땠어?"),
    MbtiQuestion(6, "IE", "대화나 약속이 끝난 뒤에 남는 리듬이 있잖아, 이번엔 어떤 쪽이었어?"),
    MbtiQuestion(7, "IE", "낯선 흐름에 들어가야 할 때가 있으면, 처음에 보통 어디서부터 시작하게 됐어?"),
    MbtiQuestion(8, "IE", "편한 사람들 사이에 있을 때는 본래보다 달라지는 모습이 있잖아, 최근엔 어땠어?"),
    MbtiQuestion(9, "IE", "혼자 있는 틈이 생겼을 때 그 시간이 충전처럼 느껴졌는지, 그냥 비는 시간처럼 느껴졌는지 궁금해."),
    MbtiQuestion(10, "IE", "뭔가를 시작해야 하는 순간에, 이번엔 어떤 계기가 있어야 몸이 움직였어?"),
    MbtiQuestion(11, "SN", "새로운 얘기를 들으면 붙잡히는 부분이 있잖아, 이번엔 뭐가 먼저 눈에 들어왔어?"),
    MbtiQuestion(12, "SN", "처음 해보는 걸 앞두면 마음이 놓이는 설명이 다르던데, 너한텐 어떤 설명이 도움 됐어?"),
    MbtiQuestion(13, "SN", "고민되는 선택 앞에서 마지막까지 남는 근거가 있잖아, 최근엔 뭐였어?"),
    MbtiQuestion(14, "SN", "길게 설명을 듣고 나면 이상하게 남는 부분이 있던데, 너는 이번에 뭐가 남았어?"),
    MbtiQuestion(15, "SN", "새 아이디어를 들으면 바로 이어지는 생각이 있잖아, 너는 그다음에 뭐가 떠올랐어?"),
    MbtiQuestion(16, "SN", "헷갈리는 일이 있을 때 이해가 딱 잡히는 포인트가 있잖아, 이번엔 뭐였어?"),
    MbtiQuestion(17, "SN", "앞으로 할 일을 떠올릴 때 머릿속에 먼저 잡히는 장면이 있잖아, 이번엔 뭐였어?"),
    MbtiQuestion(18, "SN", "낯선 주제를 만나면 확인하고 싶어지는 게 사람마다 다르던데, 너는 뭐부터 궁금했어?"),
    MbtiQuestion(19, "SN", "문제를 파악할 때 실마리가 되는 부분이 있잖아, 최근엔 어디서 찾았어?"),
    MbtiQuestion(20, "SN", "새로운 방식을 생각해볼 때 바로 살펴보게 되는 게 있잖아, 이번엔 뭐였어?"),
    MbtiQuestion(21, "TF", "결정하고 나서 마음이 편해지려면 납득돼야 하는 게 있잖아, 최근엔 뭐가 중요했어?"),
    MbtiQuestion(22, "TF", "누가 부탁하면 대답 전에 잠깐 걸리는 부분이 있잖아, 이번엔 뭐였어?"),
    MbtiQuestion(23, "TF", "의견을 전할 때 문장을 고르게 되는 기준이 있잖아, 최근엔 뭘 제일 봤어?"),
    MbtiQuestion(24, "TF", "서로 말이 안 맞을 때 먼저 풀고 싶은 지점이 생기잖아, 이번엔 뭐였어?"),
    MbtiQuestion(25, "TF", "누군가 사정을 얘기하면 판단에 남는 부분이 있잖아, 최근엔 어떻게 남았어?"),
    MbtiQuestion(26, "TF", "문제나 실수를 보면 처음 눈에 들어오는 게 사람마다 다르던데, 너는 뭐였어?"),
    MbtiQuestion(27, "TF", "같이 정해야 하는 일에서는 끝까지 놓치기 싫은 게 있잖아, 이번엔 뭐였어?"),
    MbtiQuestion(28, "TF", "불편한 말을 해야 할 때 지키고 싶은 선이 생기잖아, 최근엔 어떤 선이었어?"),
    MbtiQuestion(29, "TF", "도와줄지 고민되는 상황에서 마음을 정하게 하는 게 있잖아, 이번엔 뭐였어?"),
    MbtiQuestion(30, "TF", "결정을 설명할 때 자연스럽게 먼저 나오는 말이 있잖아, 최근엔 어떤 말이었어?"),
    MbtiQuestion(31, "JP", "할 일이 새로 생기면 첫 몇 분에 손이 가는 게 있잖아, 최근엔 뭐부터 했어?"),
    MbtiQuestion(32, "JP", "마감 있는 일은 시작되는 타이밍이 다르던데, 이번엔 어떤 흐름이었어?"),
    MbtiQuestion(33, "JP", "하루가 예상과 다르게 흘러가면 바로 손보는 게 있잖아, 최근엔 뭐였어?"),
    MbtiQuestion(34, "JP", "일이 여러 개 겹치면 머릿속에서 먼저 잡히는 게 있잖아, 이번엔 뭘 먼저 잡았어?"),
    MbtiQuestion(35, "JP", "잊으면 안 되는 일은 붙잡아두는 방식이 다르잖아, 최근엔 어떻게 챙겼어?"),
    MbtiQuestion(36, "JP", "선택지가 많아지면 마음이 편해지는 처리 방식이 있잖아, 이번엔 어떻게 했어?"),
    MbtiQuestion(37, "JP", "계획이 생기면 먼저 고정해두고 싶은 부분이 있잖아, 최근엔 뭐였어?"),
    MbtiQuestion(38, "JP", "중간에 변수가 생기면 흐름을 다시 잡는 방식이 있잖아, 이번엔 어떻게 바꿨어?"),
    MbtiQuestion(39, "JP", "미뤄둔 일이 눈에 들어올 때 손대게 되는 계기가 있잖아, 최근엔 뭐였어?"),
    MbtiQuestion(40, "JP", "일을 끝냈다고 느끼는 기준이 있잖아, 이번엔 어떤 상태가 되면 마무리였어?"),
)


def list_mbti_questions(axis: MbtiAxis | None = None) -> list[dict[str, Any]]:
    questions = MBTI_AXIS_QUESTIONS
    if axis is not None:
        questions = tuple(question for question in questions if question.axis == axis)
    return [asdict(question) for question in questions]


def get_mbti_question_by_id(question_id: int) -> dict[str, Any] | None:
    for question in MBTI_AXIS_QUESTIONS:
        if question.id == question_id:
            return asdict(question)
    return None


def get_next_mbti_question(
    asked_question_ids: list[int] | set[int] | tuple[int, ...] | None = None,
    *,
    axis: MbtiAxis | None = None,
    strategy: Literal["sequential", "random"] = "random",
    seed: int | None = None,
) -> dict[str, Any] | None:
    asked_ids = set(asked_question_ids or [])
    candidates = [
        question
        for question in MBTI_AXIS_QUESTIONS
        if question.id not in asked_ids and (axis is None or question.axis == axis)
    ]

    if not candidates:
        return None

    if strategy == "random":
        question = Random(seed).choice(candidates)
    elif strategy == "sequential":
        question = candidates[0]
    else:
        raise ValueError("strategy must be 'sequential' or 'random'.")

    return asdict(question)


def format_mbti_question_message(question: dict[str, Any] | MbtiQuestion) -> str:
    if isinstance(question, MbtiQuestion):
        question = asdict(question)
    return question["text"]


def get_asked_mbti_question_ids_from_session(session: Any) -> list[int]:
    """Return MBTI question ids already sent in this chat session.

    The current ChatMessage model has no metadata/json field, so this derives
    progress from saved assistant message content.
    """
    assistant_messages = session.messages.filter(role="assistant").only("content")
    asked_ids: list[int] = []

    for question in MBTI_AXIS_QUESTIONS:
        if any(question.text in message.content for message in assistant_messages):
            asked_ids.append(question.id)

    return asked_ids


def get_next_mbti_question_for_session(
    session: Any,
    *,
    axis: MbtiAxis | None = None,
    strategy: Literal["sequential", "random"] = "random",
    seed: int | None = None,
) -> dict[str, Any] | None:
    asked_question_ids = get_asked_mbti_question_ids_from_session(session)
    return get_next_mbti_question(
        asked_question_ids,
        axis=axis,
        strategy=strategy,
        seed=seed,
    )


def build_chatbot_response_payload(
    *,
    message: Any | None,
    question: dict[str, Any] | None,
    completed: bool,
) -> dict[str, Any]:
    """Build a response shape compatible with the existing chat API."""
    if completed:
        return {
            "id": None,
            "role": "assistant",
            "content": "MBTI 관련 질문을 모두 물어봤어.",
            "emotion_label": None,
            "created_at": None,
            "mbti_question": None,
            "mbti_question_completed": True,
        }

    if message is None or question is None:
        raise ValueError("message and question are required when completed is False.")

    created_at = getattr(message, "created_at", None)
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "emotion_label": getattr(message, "emotion_label", None),
        "created_at": created_at.isoformat() if created_at else None,
        "mbti_question": question,
        "mbti_question_completed": False,
    }


def create_mbti_question_message(
    session: Any,
    *,
    axis: MbtiAxis | None = None,
    strategy: Literal["sequential", "random"] = "random",
    seed: int | None = None,
) -> Any | None:
    """Create and return an assistant ChatMessage containing the next MBTI question."""
    question = get_next_mbti_question_for_session(
        session,
        axis=axis,
        strategy=strategy,
        seed=seed,
    )
    if question is None:
        return None

    from chat.models import ChatMessage

    return ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=format_mbti_question_message(question),
    )


def ask_mbti_question_for_session(
    session: Any,
    *,
    axis: MbtiAxis | None = None,
    strategy: Literal["sequential", "random"] = "random",
    seed: int | None = None,
    persist: bool | None = None,
) -> dict[str, Any]:
    """Session-based service entrypoint for the current Django chatbot.

    Input: ChatSession instance.
    Output: dict compatible with ChatMessageSerializer, plus MBTI metadata.
    """
    should_persist = not getattr(session, "is_secret", False) if persist is None else persist
    question = get_next_mbti_question_for_session(
        session,
        axis=axis,
        strategy=strategy,
        seed=seed,
    )

    if question is None:
        return build_chatbot_response_payload(
            message=None,
            question=None,
            completed=True,
        )

    if not should_persist:
        return {
            "id": None,
            "role": "assistant",
            "content": format_mbti_question_message(question),
            "emotion_label": None,
            "created_at": None,
            "mbti_question": question,
            "mbti_question_completed": False,
        }

    from chat.models import ChatMessage

    message = ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=format_mbti_question_message(question),
    )
    return build_chatbot_response_payload(
        message=message,
        question=question,
        completed=False,
    )


def mbti_question_node(state: dict[str, Any]) -> dict[str, Any]:
    """Standalone chatbot node that adds the next MBTI question to state.

    Expected state keys are optional:
    - asked_question_ids: list[int]
    - mbti_axis: IE/SN/TF/JP
    - question_strategy: random/sequential
    - random_seed: int
    """
    next_question = get_next_mbti_question(
        state.get("asked_question_ids"),
        axis=state.get("mbti_axis"),
        strategy=state.get("question_strategy", "random"),
        seed=state.get("random_seed"),
    )

    if next_question is None:
        return {
            **state,
            "mbti_question_completed": True,
            "current_mbti_question": None,
            "assistant_message": "MBTI 관련 질문을 모두 물어봤어.",
        }

    asked_question_ids = [*state.get("asked_question_ids", []), next_question["id"]]

    return {
        **state,
        "asked_question_ids": asked_question_ids,
        "current_mbti_question": next_question,
        "assistant_message": format_mbti_question_message(next_question),
        "mbti_question_completed": False,
    }


if __name__ == "__main__":
    demo_state: dict[str, Any] = {"asked_question_ids": [], "question_strategy": "random"}
    for _ in range(3):
        demo_state = mbti_question_node(demo_state)
        print(demo_state["assistant_message"])
