from datetime import date, datetime

from django.test import RequestFactory, TestCase
from django.utils import timezone

from chat.models import ChatMessage, ChatSession
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

from django.test import override_settings


class CalendarPermissionTests(TestCase):
    @override_settings(DEBUG=False)
    def test_production_rejects_anonymous_calendar_requests(self):
        response = self.client.get(
            '/api/calendar/month/',
            HTTP_X_BINTEUMSAI_CLIENT_ID='must-not-read-calendar',
        )

        self.assertIn(response.status_code, (401, 403))


class CalendarChatEmotionTests(TestCase):
    def test_month_includes_a_day_that_has_only_a_chat_emotion(self):
        user = User.objects.create_user(
            email='calendar-emotion@example.com',
            password='test-password',
            nickname='emotion-test',
        )
        session = ChatSession.objects.create(user=user)
        message = ChatMessage.objects.create(
            session=session,
            role='assistant',
            content='I am glad things improved.',
            emotion_label='joy',
        )
        target_datetime = timezone.make_aware(datetime(2026, 7, 20, 12, 0, 0))
        ChatMessage.objects.filter(pk=message.pk).update(created_at=target_datetime)

        self.client.force_login(user)
        response = self.client.get('/api/calendar/month/', {'year': 2026, 'month': 7})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        entry = response.json()[0]
        self.assertEqual(entry['date'], '2026-07-20')
        self.assertEqual(entry['emotion_label'], 'joy')
        self.assertFalse(entry['has_fortune'])
        self.assertIsNone(entry['checkin'])
