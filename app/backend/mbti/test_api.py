from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from mbti.models import MbtiQuestionResponse
from user.models import User


class MbtiMockQnaApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='mbti@example.com',
            password='password',
            nickname='청상아리',
            onboarding_done=True,
        )
        self.client.force_authenticate(self.user)

    @patch('mbti.services.qna_service.generate_random_axis_mbti_question')
    def test_question_endpoint_returns_question_and_axis_counts(self, mock_generate):
        mock_generate.return_value = {
            'id': None,
            'axis': 'JP',
            'text': '약속이나 할 일을 정할 때 미리 정해두는 편인가요?',
            'source': 'test',
        }

        response = self.client.get('/api/mbti/mock-qna/question/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question']['axis'], 'JP')
        self.assertEqual(
            response.data['axis_counts'],
            {'IE': 0, 'SN': 0, 'TF': 0, 'JP': 0},
        )

    def test_question_endpoint_rejects_invalid_axis(self):
        response = self.client.get('/api/mbti/mock-qna/question/?axis=XX')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('mbti.services.qna_service.generate_random_axis_mbti_question')
    def test_question_endpoint_uses_curated_bank_when_llm_fails(self, mock_generate):
        mock_generate.side_effect = RuntimeError('temporary LLM failure')

        with self.assertLogs('mbti.services.qna_service', level='WARNING'):
            response = self.client.get('/api/mbti/mock-qna/question/?axis=IE')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['question']['axis'], 'IE')
        self.assertTrue(response.data['question']['text'])

    def test_save_answer_persists_response_and_updates_counts(self):
        response = self.client.post(
            '/api/mbti/mock-qna/answer/',
            {
                'target_axis': 'JP',
                'question_text': '계획을 미리 세우는 편인가요?',
                'answer_text': '대체로 미리 정해두는 편입니다.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['axis_counts']['JP'], 1)
        saved = MbtiQuestionResponse.objects.get(id=response.data['id'])
        self.assertEqual(saved.user_id, self.user.id)
        self.assertEqual(saved.target_axis, 'JP')
        self.assertEqual(saved.question_text, '계획을 미리 세우는 편인가요?')
        self.assertEqual(saved.answer_text, '대체로 미리 정해두는 편입니다.')

    def test_save_answer_requires_question_answer_and_axis(self):
        response = self.client.post(
            '/api/mbti/mock-qna/answer/',
            {'target_axis': 'JP', 'question_text': '계획형인가요?'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_deletes_current_month_qna_data(self):
        now = timezone.now()
        current_period = now.strftime('%Y-%m')
        previous_period = '1999-01'
        current_response = MbtiQuestionResponse.objects.create(
            user_id=self.user.id,
            question_text='이번 달 질문',
            answer_text='이번 달 답변',
            target_axis='IE',
            period_key=current_period,
            answered_at=now,
            created_at=now,
        )
        previous_response = MbtiQuestionResponse.objects.create(
            user_id=self.user.id,
            question_text='지난 질문',
            answer_text='지난 답변',
            target_axis='IE',
            period_key=previous_period,
            answered_at=now,
            created_at=now,
        )

        response = self.client.delete('/api/mbti/mock-qna/reset/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['axis_counts'], {'IE': 0, 'SN': 0, 'TF': 0, 'JP': 0})
        self.assertFalse(MbtiQuestionResponse.objects.filter(id=current_response.id).exists())
        self.assertTrue(MbtiQuestionResponse.objects.filter(id=previous_response.id).exists())
