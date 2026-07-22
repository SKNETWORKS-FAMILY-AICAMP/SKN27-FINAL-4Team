from django.test import TestCase, override_settings

from .models import CharacterPreference


class CharacterPreferenceTests(TestCase):
    def test_new_preference_uses_default_expression(self):
        preference = CharacterPreference.objects.create(
            client_id="default-expression-client",
            character_id="otter",
        )

        self.assertEqual(preference.expression_id, "default")

    @override_settings(DEBUG=True)
    def test_api_accepts_default_expression(self):
        response = self.client.post(
            "/api/characters/preference/",
            {
                "character_id": "otter",
                "expression_id": "default",
            },
            content_type="application/json",
            HTTP_X_BINTEUMSAI_CLIENT_ID="default-expression-api-client",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["preference"]["expression_id"],
            "default",
        )
        self.assertTrue(
            CharacterPreference.objects.filter(
                client_id="default-expression-api-client",
                character_id="otter",
                expression_id="default",
            ).exists()
        )

from user.models import User


class CharacterOnboardingSecurityTests(TestCase):
    def test_character_selection_does_not_complete_onboarding(self):
        user = User.objects.create_user(
            email='character-onboarding@example.com',
            password='test-password',
            nickname='온보딩 테스트',
        )
        self.client.force_login(user)

        response = self.client.post(
            '/api/characters/preference/',
            {'character_id': 'otter', 'expression_id': 'default'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.character, 'toto')
        self.assertFalse(user.onboarding_done)

    @override_settings(DEBUG=False)
    def test_production_rejects_anonymous_character_requests(self):
        response = self.client.get(
            '/api/characters/preference/',
            HTTP_X_BINTEUMSAI_CLIENT_ID='must-not-create-a-user',
        )

        self.assertIn(response.status_code, (401, 403))
