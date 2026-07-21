from datetime import date

from django.test import RequestFactory, TestCase

from user.models import User

from .models import DailyFortune
from .services import save_daily_major_as_daily_fortune


class DailyMajorCalendarSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='calendar-test@example.com',
            password='test-password',
            nickname='캘린더 테스트',
        )
        self.request = RequestFactory().post('/api/tarot/daily-major/')
        self.request.user = self.user
        self.target_date = date(2026, 7, 20)

    def test_saves_the_displayed_daily_keyword_content(self):
        result = {
            'card_number': 7,
            'card_name': 'The Chariot',
            'card_name_ko': '전차',
            'card_keywords': ['전진', '의지', '승리', '통제'],
            'card_defined_meaning': '강한 의지와 추진력으로 목표를 향해 나아갈 수 있는 흐름입니다.',
            'message': '대체 메시지',
        }

        fortune = save_daily_major_as_daily_fortune(
            self.request,
            result,
            self.target_date,
        )

        self.assertEqual(DailyFortune.objects.count(), 1)
        self.assertEqual(fortune.date, self.target_date)
        self.assertEqual(fortune.topic, 'daily_major')
        self.assertEqual(fortune.title, '오늘의 카드')
        self.assertEqual(
            fortune.content,
            '강한 의지와 추진력으로 목표를 향해 나아갈 수 있는 흐름입니다.',
        )
        self.assertEqual(fortune.keyword, '전진 · 의지 · 승리 · 통제')
        self.assertEqual(fortune.cards[0]['card_name_ko'], '전차')

    def test_revealing_again_updates_the_same_calendar_day(self):
        first_result = {
            'card_number': 7,
            'card_name': 'The Chariot',
            'card_name_ko': '전차',
            'card_keywords': ['전진'],
            'card_defined_meaning': '첫 번째 내용',
        }
        updated_result = {
            **first_result,
            'card_defined_meaning': '갱신된 오늘의 키워드 내용',
        }

        save_daily_major_as_daily_fortune(self.request, first_result, self.target_date)
        fortune = save_daily_major_as_daily_fortune(
            self.request,
            updated_result,
            self.target_date,
        )

        self.assertEqual(DailyFortune.objects.count(), 1)
        self.assertEqual(fortune.content, '갱신된 오늘의 키워드 내용')
