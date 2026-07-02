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
    MbtiQuestion(1, "IE", "이번 주말에는 어떻게 시간을 보낼 때 가장 푹 쉰 것 같았어?"),
    MbtiQuestion(2, "IE", "최근에 에너지가 바닥났다고 느꼈을 때, 어떻게 충전했어?"),
    MbtiQuestion(3, "IE", "새로운 사람들과 어울려야 하는 자리에 다녀오면 기분이 어때?"),
    MbtiQuestion(4, "IE", "힘든 하루를 마치고 집에 돌아오면 제일 먼저 하고 싶은 일이 뭐야?"),
    MbtiQuestion(5, "IE", "혼자서 조용히 시간을 보낼 때 어떤 기분이 들어?"),
    MbtiQuestion(6, "IE", "친한 친구들과 시끌벅적하게 수다를 떨고 나면 에너지가 채워지는 편이야?"),
    MbtiQuestion(7, "IE", "정말 아무에게도 방해받지 않는 하루가 생기면 뭘 하고 싶어?"),
    MbtiQuestion(8, "IE", "누군가와 대화를 나누다 보면 오히려 기운이 나는 순간이 있어?"),
    MbtiQuestion(9, "IE", "최근에 혼자 있을 때 더 즐거웠어, 아니면 누군가와 함께 있을 때 더 즐거웠어?"),
    MbtiQuestion(10, "IE", "스트레스를 받을 때 사람들을 만나서 푸는 편이야, 아니면 혼자만의 시간을 가지는 편이야?"),
    MbtiQuestion(11, "SN", "어떤 새로운 소식을 들었을 때, 구체적인 사실이 먼저 궁금해 아니면 그 이면의 의미가 더 궁금해?"),
    MbtiQuestion(12, "SN", "과거의 경험을 떠올릴 때 그 당시의 디테일한 장면들이 잘 기억나는 편이야?"),
    MbtiQuestion(13, "SN", "새로운 무언가를 배울 때 이론부터 파악하는 게 좋아, 아니면 일단 직접 해보면서 익히는 게 좋아?"),
    MbtiQuestion(14, "SN", "미래를 상상할 때 일어날 법한 현실적인 그림을 그리는 편이야, 아니면 완전히 색다른 가능성을 떠올려?"),
    MbtiQuestion(15, "SN", "이야기를 들을 때 '그래서 정확히 무슨 일이 있었던 건데?'라는 생각이 자주 들어?"),
    MbtiQuestion(16, "SN", "비유나 은유적인 표현을 들으면 금방 와닿는 편이야?"),
    MbtiQuestion(17, "SN", "지금 당장 눈앞에 주어진 문제에 집중하는 게 편해, 아니면 장기적인 방향성을 고민하는 게 편해?"),
    MbtiQuestion(18, "SN", "요리를 하거나 조립을 할 때 설명서를 꼼꼼히 따라가는 편이야?"),
    MbtiQuestion(19, "SN", "가끔 현실과는 전혀 상관없는 엉뚱한 상상에 빠지기도 해?"),
    MbtiQuestion(20, "SN", "숲 전체를 먼저 보려고 해, 아니면 나무 하나하나를 자세히 보는 편이야?"),
    MbtiQuestion(21, "TF", "친구가 고민을 털어놓을 때, 어떻게 해결할지 답을 찾아주는 게 먼저야 아니면 공감해주는 게 먼저야?"),
    MbtiQuestion(22, "TF", "어떤 결정을 내릴 때 내 감정이나 사람들의 관계가 얼마나 영향을 미쳐?"),
    MbtiQuestion(23, "TF", "논리적으로는 맞지만 누군가가 상처받을 수 있는 상황이라면 어떻게 할 것 같아?"),
    MbtiQuestion(24, "TF", "다른 사람의 입장에 이입해서 같이 속상해하거나 기뻐하는 일이 잦은 편이야?"),
    MbtiQuestion(25, "TF", "원칙과 규칙을 지키는 것과 상황에 따라 융통성을 발휘하는 것 중 어느 쪽이 더 끌려?"),
    MbtiQuestion(26, "TF", "영화나 드라마를 볼 때 등장인물의 감정선에 깊이 빠져드는 편이야?"),
    MbtiQuestion(27, "TF", "누군가를 설득해야 할 때 사실과 데이터가 더 효과적이라고 생각해, 아니면 진정성 있는 태도가 중요하다고 생각해?"),
    MbtiQuestion(28, "TF", "주변 사람들이 슬퍼하면 나도 모르게 기분이 쳐지는 편이야?"),
    MbtiQuestion(29, "TF", "객관적이고 이성적이라는 평가를 들으면 기분이 어때?"),
    MbtiQuestion(30, "TF", "비판을 받을 때 그 내용의 타당성보다 말하는 사람의 어투에 더 신경 쓰이기도 해?"),
    MbtiQuestion(31, "JP", "여행을 갈 때 미리 시간대별로 계획을 세워두는 편이야, 아니면 발길 닿는 대로 다니는 편이야?"),
    MbtiQuestion(32, "JP", "할 일이 주어지면 마감일 훨씬 전부터 미리미리 해두어야 마음이 편해?"),
    MbtiQuestion(33, "JP", "상황이 갑자기 바뀌어서 일정이 틀어지면 스트레스를 많이 받는 편이야?"),
    MbtiQuestion(34, "JP", "방이나 책상을 항상 깔끔하게 정리정돈 해두는 걸 좋아해?"),
    MbtiQuestion(35, "JP", "결정을 내리기 전에 최대한 많은 선택지를 열어두고 마지막까지 고민하는 편이야?"),
    MbtiQuestion(36, "JP", "해야 할 일의 목록을 만들고 하나씩 지워나갈 때 쾌감을 느껴?"),
    MbtiQuestion(37, "JP", "주말 일정이 정해져 있지 않고 텅 비어있을 때 더 설레고 좋아?"),
    MbtiQuestion(38, "JP", "약속 시간에 늦는 것에 대해 어떻게 생각해?"),
    MbtiQuestion(39, "JP", "시작한 일은 끝을 맺어야 직성이 풀리는 편이야?"),
    MbtiQuestion(40, "JP", "일할 때 중간중간 휴식을 취하며 유연하게 하는 편이야, 아니면 집중해서 끝내놓고 쉬는 편이야?"),
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
