from datetime import date
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from user.models import User

from .views import daily_major_fortune


class DailyMajorRevealViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='daily-major-view@example.com',
            password='test-password',
            nickname='오늘의 카드 테스트',
        )
        self.factory = APIRequestFactory()
        self.daily_result = {
            'id': 11,
            'target_date': '2026-07-20',
            'card_number': 7,
            'card_name': 'The Chariot',
            'card_name_ko': '전차',
            'card_keywords': ['전진', '의지'],
            'card_defined_meaning': '오늘의 키워드 내용',
        }

    @patch('game.tarot_api.views.DailyFortuneSerializer')
    @patch('game.tarot_api.views.DailyTarotFortuneSerializer')
    @patch('game.tarot_api.views.save_daily_major_as_daily_fortune')
    @patch('game.tarot_api.views.get_or_create_daily_major_fortune')
    def test_post_reveals_and_saves_the_daily_card(
        self,
        get_daily_major,
        save_daily_major,
        tarot_serializer,
        daily_fortune_serializer,
    ):
        tarot_fortune = object()
        saved_fortune = object()
        get_daily_major.return_value = tarot_fortune
        tarot_serializer.return_value.data = self.daily_result.copy()
        save_daily_major.return_value = saved_fortune
        daily_fortune_serializer.return_value.data = {'id': 31, 'content': '오늘의 키워드 내용'}

        request = self.factory.post(
            '/api/tarot/daily-major/',
            {'date': '2026-07-20'},
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = daily_major_fortune(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['daily_fortune']['content'], '오늘의 키워드 내용')
        save_daily_major.assert_called_once()
        called_request, called_result, called_date = save_daily_major.call_args.args
        self.assertEqual(called_request.user, self.user)
        self.assertEqual(called_result, self.daily_result)
        self.assertEqual(called_date, date(2026, 7, 20))

    @patch('game.tarot_api.views.DailyTarotFortuneSerializer')
    @patch('game.tarot_api.views.save_daily_major_as_daily_fortune')
    @patch('game.tarot_api.views.get_or_create_daily_major_fortune')
    def test_get_only_loads_the_daily_card_without_calendar_save(
        self,
        get_daily_major,
        save_daily_major,
        tarot_serializer,
    ):
        get_daily_major.return_value = object()
        tarot_serializer.return_value.data = self.daily_result.copy()

        request = self.factory.get('/api/tarot/daily-major/', {'date': '2026-07-20'})
        force_authenticate(request, user=self.user)

        response = daily_major_fortune(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('daily_fortune', response.data)
        save_daily_major.assert_not_called()
