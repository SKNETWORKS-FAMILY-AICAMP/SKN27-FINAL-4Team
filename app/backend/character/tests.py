from django.test import TestCase

from .models import CharacterPreference


class CharacterPreferenceTests(TestCase):
    def test_new_preference_uses_default_expression(self):
        preference = CharacterPreference.objects.create(
            client_id="default-expression-client",
            character_id="otter",
        )

        self.assertEqual(preference.expression_id, "default")

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
