from django.test import SimpleTestCase

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
