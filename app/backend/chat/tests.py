# -*- coding: utf-8 -*-
"""챗봇 API 테스트.

실행: python manage.py test chat   (Postgres 불필요 — 테스트는 sqlite 사용)
LLM 호출이 필요한 경로(chat_turn 본 플로우)는 스모크 테스트 후 mock 기반으로 추가 예정.
"""
from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APITestCase

from ai.emotion.emotion_model import is_active, predict_emotion
from .models import ChatMessage, ChatSession


class SideApiTests(APITestCase):
    """부가 기능 — 날씨/추천질문/피드백/감정모델 폴백"""

    def test_weather_opener_fallback(self):
        """날씨 API — 외부 API 실패 시에도 200 + 기본 opener 반환"""
        mock_fail = MagicMock()
        mock_fail.status_code = 500
        with patch('requests.get', return_value=mock_fail):
            response = self.client.get('/api/chat/weather-opener/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('opener', response.data)

    @patch('chat.views._client')
    def test_suggest_questions_api(self, mock_client):
        """이런 말 어때요? 추천 질문 생성"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"questions": ["a", "b", "c"]}'
        mock_client.return_value.chat.completions.create.return_value = mock_response

        session = ChatSession.objects.create(character='pori', is_secret=False)
        ChatMessage.objects.create(session=session, role='user', content='요즘 우울해')

        resp = self.client.post(f'/api/chat/sessions/{session.id}/questions/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['questions']), 3)

    def test_emotion_model_loader_fallback(self):
        """감정모델 산출물이 없어도 예외 없이 None 폴백"""
        result = predict_emotion('오늘 정말 행복해!')
        self.assertTrue(result is None or isinstance(result, str))
        self.assertIsInstance(is_active(), bool)


class V6FlowTests(APITestCase):
    """v6.0 메인 플로우 — 세션/콜드스타트/검증 로직 (LLM 호출 없는 경로)"""

    def test_session_start_returns_cold_start_choices(self):
        resp = self.client.post('/api/session/start/',
                                {'character_id': 'pori', 'is_secret': False}, format='json')
        self.assertEqual(resp.status_code, 201)
        data = resp.data['data']
        self.assertFalse(data['cold_start_done'])
        self.assertEqual(len(data['emotion_choices']), 4)

    def test_invalid_character_rejected(self):
        resp = self.client.post('/api/session/start/',
                                {'character_id': 'sodam', 'is_secret': False}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['error']['code'], 'INVALID_CHARACTER')

    def test_chat_requires_cold_start(self):
        start = self.client.post('/api/session/start/',
                                 {'character_id': 'toto', 'is_secret': False}, format='json')
        sid = start.data['data']['session_id']
        resp = self.client.post('/api/chat/',
                                {'session_id': sid, 'character_id': 'toto',
                                 'message': '안녕', 'is_secret': False}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['error']['code'], 'COLD_START_REQUIRED')

    def test_cold_start_flow(self):
        start = self.client.post('/api/session/start/',
                                 {'character_id': 'yeoul', 'is_secret': False}, format='json')
        sid = start.data['data']['session_id']
        resp = self.client.post('/api/session/cold-start/',
                                {'session_id': sid, 'selected_emotion': 'sadness'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['data']['cold_start_done'])
        self.assertIn('tts_task_id', resp.data['data'])

    def test_tts_task_not_found(self):
        resp = self.client.get('/api/tts/tts_none/')
        self.assertEqual(resp.status_code, 404)

    def test_session_end(self):
        start = self.client.post('/api/session/start/',
                                 {'character_id': 'kkami', 'is_secret': True}, format='json')
        sid = start.data['data']['session_id']
        resp = self.client.post('/api/session/end/', {'session_id': sid}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['data']['ended'])
