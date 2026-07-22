from django.test import SimpleTestCase, TestCase, override_settings

from .models import User
from .serializers import UserPersonalProfileSerializer


class AgreementValidationTests(SimpleTestCase):
    def test_requires_overseas_transfer_consent(self):
        serializer = UserPersonalProfileSerializer(data={
            'agreements': {
                'termsOfService': True,
                'privacyCollection': True,
                'overseasTransfer': False,
            },
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('agreements', serializer.errors)

    def test_accepts_all_required_consents(self):
        serializer = UserPersonalProfileSerializer(data={
            'agreements': {
                'termsOfService': True,
                'privacyCollection': True,
                'overseasTransfer': True,
            },
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

class ProfilePermissionTests(TestCase):
    @override_settings(DEBUG=False)
    def test_production_rejects_anonymous_profile_requests(self):
        response = self.client.get(
            '/api/user/profile/',
            HTTP_X_BINTEUMSAI_CLIENT_ID='must-not-create-a-user',
        )

        self.assertIn(response.status_code, (401, 403))

    def test_completed_user_is_sent_to_home_after_login(self):
        user = User.objects.create_user(
            email='completed-onboarding@example.com',
            password='test-password',
            nickname='완료 사용자',
            onboarding_done=True,
        )
        self.client.force_login(user)

        response = self.client.get('/api/user/me/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['next_path'], '/home')
