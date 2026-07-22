from datetime import date
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from user.models import User, UserPreferenceKeyword

from .models import CauseContextConfig, CauseOption, DailyCheckin, RecommendationAction, ReflectionOption


class CheckinApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        output = StringIO()
        call_command('import_checkin_content', stdout=output)
        cls.user = User.objects.create_user('checkin@example.com', password='password123', nickname='테스트', character='pori', onboarding_done=True)
        cls.other = User.objects.create_user('other@example.com', password='password123', nickname='다른 사용자', character='pori', onboarding_done=True)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch('checkin.services._llm_generated_actions')
    def test_selection_only_flow_and_recommendations(self, mock_llm_actions):
        UserPreferenceKeyword.objects.create(user=self.user, keyword_type='interest', label='사진촬영')
        UserPreferenceKeyword.objects.create(user=self.user, keyword_type='interest', label='맛집탐방')
        UserPreferenceKeyword.objects.create(user=self.user, keyword_type='hobby', label='배드민턴')
        UserPreferenceKeyword.objects.create(user=self.user, keyword_type='hobby', label='헬스')
        mock_llm_actions.return_value = [
            {
                'title': '사진촬영 산책하기',
                'description': '사진촬영을 하며 집 근처에서 마음에 드는 장면 세 곳을 찾아보세요.',
                'duration': '20분',
                'icon': '📷',
                'tags': ['관심사', '사진촬영'],
                'reason': '사진촬영에 집중하며 생각을 잠시 환기할 수 있어요.',
                'source': 'interest',
                'source_keyword': '사진촬영',
            },
            {
                'title': '맛집탐방 목록 고르기',
                'description': '맛집탐방 후보 중 이번 주에 가보고 싶은 곳 한 곳을 저장해보세요.',
                'duration': '10분',
                'icon': '🍽️',
                'tags': ['관심사', '맛집탐방'],
                'reason': '맛집탐방 계획을 세우며 가벼운 기대를 만들 수 있어요.',
                'source': 'interest',
                'source_keyword': '맛집탐방',
            },
            {
                'title': '배드민턴 한 게임 치기',
                'description': '친구와 배드민턴을 한 게임 치며 몸을 가볍게 움직여보세요.',
                'duration': '40분',
                'icon': '🏸',
                'tags': ['취미', '배드민턴'],
                'reason': '배드민턴으로 답답한 에너지를 건강하게 풀 수 있어요.',
                'source': 'hobby',
                'source_keyword': '배드민턴',
            },
            {
                'title': '헬스장 웨이트하기',
                'description': '헬스장에서 익숙한 웨이트 운동을 무리하지 않는 강도로 해보세요.',
                'duration': '50분',
                'icon': '🏋️',
                'tags': ['취미', '헬스'],
                'reason': '헬스로 몸의 긴장을 천천히 풀 수 있어요.',
                'source': 'hobby',
                'source_keyword': '헬스',
            },
        ]
        bootstrap = self.client.get('/api/checkin/bootstrap/')
        self.assertEqual(bootstrap.status_code, 200)
        self.assertFalse(bootstrap.data['data']['has_checkin'])

        created = self.client.post('/api/checkin/', {}, format='json')
        self.assertEqual(created.status_code, 201)
        checkin_id = created.data['data']['checkin_id']

        reflection = self.client.patch(f'/api/checkin/{checkin_id}/reflection/', {'reflection_id': 'DAY-003'}, format='json')
        self.assertEqual(reflection.status_code, 200)
        self.assertEqual(reflection.data['data']['stage'], 'CAUSE')
        self.assertNotIn('일이나 공부', [item['label'] for item in reflection.data['data']['options']['reflection']])

        cause = self.client.patch(f'/api/checkin/{checkin_id}/cause/', {'cause_id': 'CAUSE-001'}, format='json')
        self.assertEqual(cause.status_code, 200)
        self.assertEqual(cause.data['data']['stage'], 'NEED')

        need = self.client.patch(f'/api/checkin/{checkin_id}/need/', {'need_id': 'NEED-003'}, format='json')
        self.assertEqual(need.status_code, 200)
        self.assertEqual(need.data['data']['stage'], 'RECOMMENDATION')

        recommendations = self.client.post(f'/api/checkin/{checkin_id}/recommendations/', {}, format='json')
        self.assertEqual(recommendations.status_code, 200)
        items = recommendations.data['data']['recommendations']
        self.assertEqual(len(items), 4)
        self.assertTrue(all(item.get('id') and item.get('action_id') and item.get('title') and item.get('description') for item in items))

        completed = self.client.post(f'/api/checkin/{checkin_id}/complete/', {
            'final_route': 'ACTION', 'selected_action_id': items[0]['action_id'],
        }, format='json')
        self.assertEqual(completed.status_code, 200)
        self.assertTrue(completed.data['data']['completed'])

        feedback = self.client.post(f'/api/checkin/{checkin_id}/feedback/', {
            'action_id': items[0]['action_id'], 'completed': True, 'helpfulness': 2,
        }, format='json')
        self.assertEqual(feedback.status_code, 200)

    def test_other_user_checkin_is_not_accessible(self):
        other = DailyCheckin.objects.create(user=self.other, checkin_date=date.today())
        response = self.client.patch(f'/api/checkin/{other.id}/reflection/', {'reflection_id': 'DAY-001'}, format='json')
        self.assertEqual(response.status_code, 404)

    def test_import_is_idempotent_and_date_is_unique(self):
        before = ReflectionOption.objects.count()
        call_command('import_checkin_content', stdout=StringIO())
        self.assertEqual(ReflectionOption.objects.count(), before)
        DailyCheckin.objects.create(user=self.user, checkin_date=date.today())
        with self.assertRaises(IntegrityError):
            DailyCheckin.objects.create(user=self.user, checkin_date=date.today())

    def test_cause_context_selects_context_specific_text_and_skip_skips_cause(self):
        ReflectionOption.objects.update_or_create(
            reflection_id='DAY-POSITIVE',
            defaults={'label': '기분이 좋았어', 'primary_emotion': 'JOY', 'cause_context': 'POSITIVE', 'energy_level': 'MEDIUM'},
        )
        ReflectionOption.objects.update_or_create(
            reflection_id='DAY-SKIP',
            defaults={'label': '자세히 말하고 싶지 않아', 'primary_emotion': '', 'cause_context': 'SKIP', 'next_stage': 'NEED', 'energy_level': 'UNKNOWN'},
        )
        CauseContextConfig.objects.update_or_create(
            cause_context='POSITIVE',
            defaults={'title': '기분 좋은 계기', 'question_text': '오늘 기분을 좋게 만든 건 뭐였어?', 'option_text_field': 'option_text_positive'},
        )
        CauseOption.objects.update_or_create(
            cause_id='CAUSE-BRANCH',
            defaults={'cause_code': 'BRANCH', 'label': '기본 원인', 'available_contexts': ['POSITIVE'], 'option_text_positive': '일이나 공부에서 뿌듯한 일이 있었어'},
        )
        checkin = self.client.post('/api/checkin/', {}, format='json').data['data']['checkin_id']
        positive = self.client.patch(f'/api/checkin/{checkin}/reflection/', {'reflection_id': 'DAY-POSITIVE'}, format='json')
        self.assertEqual(positive.data['data']['cause_context'], 'POSITIVE')
        self.assertEqual(positive.data['data']['cause_title'], '기분 좋은 계기')
        self.assertEqual(positive.data['data']['cause_options'][0]['label'], '일이나 공부에서 뿌듯한 일이 있었어')
        self.client.patch(f'/api/checkin/{checkin}/cause/', {'cause_id': 'CAUSE-BRANCH'}, format='json')

        skip = self.client.post('/api/checkin/', {}, format='json').data['data']['checkin_id']
        skipped = self.client.patch(f'/api/checkin/{skip}/reflection/', {'reflection_id': 'DAY-SKIP'}, format='json')
        self.assertEqual(skipped.data['data']['stage'], 'NEED')
        self.assertEqual(skipped.data['data']['cause_options'], [])
