from __future__ import annotations

from test.jaewung.mbti_analyzer.analyzer.schemas import ConversationMessage, LocalContextWindow


class LocalContextBuilder:
    def build_windows(
        self,
        messages: list[ConversationMessage],
    ) -> list[LocalContextWindow]:
        sorted_messages = sorted(
            messages,
            key=lambda m: (m.conversation_id, m.turn_index),
        )

        windows: list[LocalContextWindow] = []

        for idx, message in enumerate(sorted_messages):
            if message.role != "user":
                continue

            same_conversation = [
                m for m in sorted_messages
                if m.conversation_id == message.conversation_id
            ]
            local_idx = same_conversation.index(message)

            previous_user = self._find_previous(
                same_conversation,
                local_idx,
                role="user",
            )
            previous_assistant = self._find_previous(
                same_conversation,
                local_idx,
                role="assistant",
            )
            next_user = self._find_next(
                same_conversation,
                local_idx,
                role="user",
            )

            context_parts: list[str] = []
            context_message_ids: list[str] = []

            if previous_user:
                context_parts.append(f"직전 user: {previous_user.raw_text}")
                context_message_ids.append(previous_user.message_id)

            if previous_assistant:
                context_parts.append(f"직전 assistant: {previous_assistant.raw_text}")
                context_message_ids.append(previous_assistant.message_id)

            context_parts.append(f"분석 대상 user: {message.raw_text}")
            context_message_ids.append(message.message_id)

            if next_user:
                context_parts.append(f"직후 user: {next_user.raw_text}")
                context_message_ids.append(next_user.message_id)

            windows.append(
                LocalContextWindow(
                    target_message_id=message.message_id,
                    user_id=message.user_id,
                    conversation_id=message.conversation_id,
                    source_created_at=message.created_at,
                    target_user_text=message.raw_text,
                    context_text="\n".join(context_parts),
                    context_message_ids=context_message_ids,
                )
            )

        return windows

    def _find_previous(
        self,
        messages: list[ConversationMessage],
        idx: int,
        role: str,
    ) -> ConversationMessage | None:
        for prev_idx in range(idx - 1, -1, -1):
            if messages[prev_idx].role == role:
                return messages[prev_idx]
        return None

    def _find_next(
        self,
        messages: list[ConversationMessage],
        idx: int,
        role: str,
    ) -> ConversationMessage | None:
        for next_idx in range(idx + 1, len(messages)):
            if messages[next_idx].role == role:
                return messages[next_idx]
        return None