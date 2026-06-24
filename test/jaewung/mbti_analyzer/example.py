from datetime import datetime
from pprint import pprint

from test.jaewung.mbti_analyzer.analyzer.llm_coder import LangChainOpenAIMbtiCoder
from test.jaewung.mbti_analyzer.analyzer.schemas import ConversationMessage
from test.jaewung.mbti_analyzer.analyzer.service import MbtiAnalysisService


def main() -> None:
    messages = [
        ConversationMessage(
            message_id="a1",
            user_id=1,
            conversation_id="conv_1",
            role="assistant",
            raw_text="이번 주말에 사람들과 약속을 잡아보는 건 어때요?",
            turn_index=1,
            created_at=datetime(2026, 6, 10, 20, 10),
        ),
        ConversationMessage(
            message_id="u1",
            user_id=1,
            conversation_id="conv_1",
            role="user",
            raw_text="좋긴 한데 약속 끝나면 혼자 조용히 있어야 회복돼요.",
            turn_index=2,
            created_at=datetime(2026, 6, 10, 20, 11),
        ),
        ConversationMessage(
            message_id="a2",
            user_id=1,
            conversation_id="conv_1",
            role="assistant",
            raw_text="그럼 다음 계획은 어떻게 잡고 싶으세요?",
            turn_index=3,
            created_at=datetime(2026, 6, 10, 20, 12),
        ),
        ConversationMessage(
            message_id="u2",
            user_id=1,
            conversation_id="conv_1",
            role="user",
            raw_text="확정하기보다는 일단 선택지를 열어두고 상황을 보고 싶어요.",
            turn_index=4,
            created_at=datetime(2026, 6, 10, 20, 13),
        ),
        ConversationMessage(
            message_id="u3",
            user_id=1,
            conversation_id="conv_1",
            role="user",
            raw_text="원인을 먼저 정리해보고, 그 다음에 결정하는 게 좋겠어요.",
            turn_index=5,
            created_at=datetime(2026, 6, 10, 20, 14),
        ),
    ]

    coder = LangChainOpenAIMbtiCoder()
    service = MbtiAnalysisService(coder=coder)

    output = service.analyze(
        user_id=1,
        period_type="monthly",
        period_key="2026-06",
        messages=messages,
    )

    print("\n--- message_mbti_evidence ---")
    pprint([record.model_dump() for record in output.message_mbti_evidence])

    print("\n--- mbti_period_result ---")
    pprint(output.mbti_period_result.model_dump())

    print("\n--- dashboard ---")
    pprint(output.dashboard.model_dump())


if __name__ == "__main__":
    main()