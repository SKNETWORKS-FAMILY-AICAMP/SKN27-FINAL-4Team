from django.core.management import call_command
from django.test import TestCase, override_settings

from user.models import User


@override_settings(EMOTION_CARD_ENABLE_REAL_IMAGE_API=False)
class EmotionCardApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('import_emotion_card_data')
        cls.user = User.objects.create_user(email='emotion-card@example.com', password='password', nickname='마음이', character='pori', onboarding_done=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_analysis_scene_generation_and_feedback_flow(self):
        analysis_response = self.client.post('/api/emotion-cards/analyze/', {
            'emotion_text': '발표를 마치고 안도하면서도 조금 긴장돼.',
            'event_text': '발표를 잘 마침',
            'energy_code': 'ENG_STEADY',
            'need_code': 'NEED_COMFORT',
        }, content_type='application/json')
        self.assertEqual(analysis_response.status_code, 201)
        analysis_id = analysis_response.json()['analysis_id']

        scene_response = self.client.post(f'/api/emotion-cards/analyses/{analysis_id}/scene/')
        self.assertEqual(scene_response.status_code, 201)
        scene = scene_response.json()
        self.assertTrue(scene['available_styles'])

        generation_response = self.client.post(
            f"/api/emotion-cards/scenes/{scene['scene_id']}/generate/",
            {'style_id': scene['available_styles'][0]['style_id'], 'idempotency_key': 'test-card-job'}, content_type='application/json')
        self.assertEqual(generation_response.status_code, 202)
        job = self.client.get(f"/api/emotion-cards/jobs/{generation_response.json()['job_id']}/").json()
        self.assertEqual(job['status'], 'COMPLETED')
        self.assertTrue(job['card_id'])
        card = self.client.get(f"/api/emotion-cards/{job['card_id']}/").json()
        self.assertTrue(card['image_url'])

        feedback = self.client.post(f"/api/emotion-cards/{job['card_id']}/feedback/", {'helpful': True}, content_type='application/json')
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()['feedback']['helpful'])

    def test_unauthenticated_request_is_rejected(self):
        self.client.logout()
        response = self.client.post('/api/emotion-cards/analyze/', {'emotion_text': '오늘은 괜찮아.'}, content_type='application/json')
        self.assertEqual(response.status_code, 401)
