from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from ai.agents.mbti import generate_question
from ai.agents.nodes import mbti_check_node, mbti_save_node
from chat.models import MbtiAnswer
from mbti.models import MbtiQuestionResponse
from user.models import User


class ChatMbtiFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='chat-mbti-flow@example.com',
            password='password',
            nickname='MBTI흐름검증',
            onboarding_done=True,
        )

    @patch('ai.agents.nodes._mbti_answer_check_llm')
    def test_answer_check_uses_dedicated_mbti_classifier(self, mock_llm):
        mock_llm.return_value.invoke.return_value = SimpleNamespace(content='yes')

        result = mbti_check_node({
            'mbti_question_text': '주말에는 혼자 쉬어야 충전되는 편이야?',
            'user_message': '응, 혼자 책을 읽고 쉬면 기운이 돌아와.',
        })

        self.assertTrue(result['is_mbti_answer'])
        self.assertEqual(mock_llm.call_args.kwargs['max_tokens'], 128)

    @patch('ai.agents.nodes._llm')
    def test_save_uses_the_question_actually_shown_to_the_user(self, mock_llm):
        mock_llm.return_value.invoke.return_value = SimpleNamespace(content='고마워!')
        displayed_question = '방금 모임에서 돌아왔을 때 혼자 쉬고 싶었어, 더 이야기하고 싶었어?'

        result = mbti_save_node({
            'user_id': self.user.id,
            'session_id': 1234,
            'session_mode': 'normal',
            'user_message': '혼자 조용히 쉬면서 충전하고 싶었어.',
            'mbti_question_code': 'IE_1',
            'mbti_question_text': displayed_question,
        })

        self.assertTrue(result['mbti_saved'])
        self.assertEqual(MbtiAnswer.objects.get().question_code, 'IE_1')
        saved = MbtiQuestionResponse.objects.get()
        self.assertEqual(saved.question_text, displayed_question)
        self.assertEqual(saved.answer_text, '혼자 조용히 쉬면서 충전하고 싶었어.')

    @patch('ai.agents.llm.get_llm')
    @patch('ai.agents.mbti._next_code', return_value='IE_1')
    def test_contextual_question_allows_reasoning_model_output_budget(
        self, mock_next_code, mock_get_llm
    ):
        mock_get_llm.return_value.invoke.return_value = SimpleNamespace(
            content='오늘처럼 여유로운 날엔 혼자 쉬는 게 좋아, 사람을 만나는 게 좋아?'
        )

        code, text = generate_question(self.user, [])

        self.assertEqual(code, 'IE_1')
        self.assertIn('오늘처럼', text)
        self.assertEqual(mock_get_llm.call_args.kwargs['max_tokens'], 320)
