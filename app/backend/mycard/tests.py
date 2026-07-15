from datetime import date

from rest_framework.test import APITestCase

from user.models import User

from .models import MyCard


class MyCardApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='mycard@example.com',
            password='password123',
            nickname='카드 사용자',
            character='pori',
            onboarding_done=True,
        )
        self.other = User.objects.create_user(
            email='mycard-other@example.com',
            password='password123',
            nickname='다른 사용자',
            character='pori',
            onboarding_done=True,
        )
        self.client.force_authenticate(self.user)
        self.payload = {
            'sky': 'SUNSET',
            'pace': 'SLOW',
            'space': 'SEA',
            'phrase': 'TIRED',
            'free_text': '따뜻한 음료를 마시며 창밖을 보고 싶은 느낌',
            'style': 'WATERCOLOR',
            'custom_style': None,
        }

    def test_unauthenticated_bootstrap_returns_401(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/mycard/bootstrap/')
        self.assertEqual(response.status_code, 401)

    def test_generate_save_and_daily_limit(self):
        bootstrap = self.client.get('/api/mycard/bootstrap/')
        self.assertEqual(bootstrap.status_code, 200)
        self.assertEqual(bootstrap.data['today_generation_count'], 0)

        first = self.client.post('/api/mycard/generate/', self.payload, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertTrue(first.data['id'])
        self.assertEqual(first.data['image_url'], '')
        self.assertTrue(first.data['title'])
        self.assertTrue(first.data['description'])

        save_response = self.client.post(f"/api/mycard/{first.data['id']}/save/", {}, format='json')
        self.assertEqual(save_response.status_code, 200)
        self.assertTrue(MyCard.objects.get(id=first.data['id']).is_saved)

        second = self.client.post('/api/mycard/generate/', self.payload, format='json')
        self.assertEqual(second.status_code, 201)
        limited = self.client.post('/api/mycard/generate/', self.payload, format='json')
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.data['error']['code'], 'MY_CARD_DAILY_LIMIT')

        bootstrap = self.client.get('/api/mycard/bootstrap/')
        self.assertEqual(bootstrap.data['today_generation_count'], 2)

    def test_style_or_custom_style_is_required(self):
        payload = {**self.payload, 'style': '', 'custom_style': None}
        response = self.client.post('/api/mycard/generate/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'INVALID_MY_CARD_REQUEST')

    def test_save_rejects_another_users_card(self):
        card = MyCard.objects.create(
            user=self.other,
            date=date.today(),
            sky='CLEAR',
            pace='NORMAL',
            space='CAFE',
            phrase='OKAY',
        )
        response = self.client.post(f'/api/mycard/{card.id}/save/', {}, format='json')
        self.assertEqual(response.status_code, 404)
