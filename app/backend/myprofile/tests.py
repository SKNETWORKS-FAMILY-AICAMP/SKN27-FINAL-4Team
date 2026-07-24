from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from character.models import CharacterPreference
from user.models import User, UserProfile
from mybook.views import _build_user_profile
from chat.models import ChatMessage, ChatSession


class MyProfileApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='mypage@example.com',
            password='password',
            nickname='청상아리',
            character='pori',
            onboarding_done=True,
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            job='무직',
            birth_date=date(1997, 3, 25),
            gender='남',
            interests=['심리', '반려동물', '드라마', '디지털 트렌드'],
            hobbies=['음악 감상', '카페 투어', '산책'],
        )

    def test_profile_requires_login(self):
        response = self.client.get('/api/myprofile/profile/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_load_mypage_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/myprofile/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = response.data['profile']
        self.assertEqual(profile['name'], '청상아리')
        self.assertEqual(profile['job'], '무직')
        self.assertEqual(profile['birthDate'], '1997.03.25')
        self.assertEqual(profile['gender'], '남')
        self.assertEqual(profile['interests'], ['심리', '반려동물', '드라마', '디지털 트렌드'])
        self.assertEqual(profile['hobbies'], ['음악 감상', '카페 투어', '산책'])
        self.assertEqual(profile['selectedCharacter'], 'redpanda')
        self.assertEqual(profile['account']['email'], 'mypage@example.com')
        self.assertEqual(profile['account']['provider'], 'Email')

    def test_onboarding_character_preference_is_immediately_returned_for_mypage(self):
        CharacterPreference.objects.create(
            user=self.user,
            character_id='cat',
            expression_id='joy',
        )
        self.user.character = 'kkami'
        self.user.save(update_fields=['character'])
        self.client.force_authenticate(self.user)

        response = self.client.get('/api/myprofile/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['profile']['selectedCharacter'], 'cat')

    def test_today_emotion_returns_recency_weighted_assistant_emotion(self):
        self.client.force_authenticate(self.user)
        session = ChatSession.objects.create(user=self.user, character='pori')
        ChatMessage.objects.create(
            session=session,
            role='user',
            content='사용자 행의 라벨은 대표 감정에서 제외되어야 한다.',
            emotion_label='anger',
        )
        for label in ('joy', 'joy', 'joy', 'sadness', 'sadness'):
            ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=f'{label} 응답',
                emotion_label=label,
            )

        response = self.client.get('/api/myprofile/today-emotion/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_count'], 5)
        self.assertEqual(response.data['representative']['key'], 'sadness')
        self.assertEqual(response.data['representative']['label'], '슬픔')
        self.assertEqual(response.data['dominant'][0]['key'], 'joy')
        self.assertEqual(_build_user_profile(self.user)['today_emotion'], '슬픔')
        self.assertNotIn(
            'anger',
            {item['key'] for item in response.data['distribution']},
        )

    def test_authenticated_user_without_onboarding_profile_gets_404(self):
        user = User.objects.create_user(
            email='without-profile@example.com',
            password='password',
            nickname='프로필없음',
        )
        self.client.force_authenticate(user)

        response = self.client.get('/api/myprofile/profile/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'Onboarding profile not found.')

    def test_authenticated_user_can_update_profile_fields(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            '/api/myprofile/profile/',
            {
                'profile': {
                    'name': '새닉네임',
                    'job': '개발자',
                    'birthDate': '1998.04.26',
                    'gender': '여',
                    'interests': ['음악', '관계'],
                    'hobbies': ['산책'],
                    'selectedCharacter': 'toto',
                }
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.nickname, '새닉네임')
        self.assertEqual(self.user.character, 'toto')
        self.assertEqual(self.profile.job, '개발자')
        self.assertEqual(self.profile.birth_date, date(1998, 4, 26))
        self.assertEqual(self.profile.gender, '여')
        self.assertEqual(self.profile.interests, ['음악', '관계'])
        self.assertEqual(self.profile.hobbies, ['산책'])
        self.assertEqual(response.data['profile']['name'], '새닉네임')
        self.assertEqual(response.data['profile']['selectedCharacter'], 'otter')
        self.assertTrue(
            CharacterPreference.objects.filter(
                user=self.user,
                character_id='otter',
            ).exists()
        )

    def test_partial_interest_update_preserves_other_profile_fields_for_books(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            '/api/myprofile/profile/',
            {'profile': {'interests': ['천문학', '과학사']}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.nickname, '청상아리')
        self.assertEqual(self.user.character, 'pori')
        self.assertEqual(self.profile.interests, ['천문학', '과학사'])
        self.assertEqual(self.profile.hobbies, ['음악 감상', '카페 투어', '산책'])
        self.assertEqual(response.data['profile']['interests'], ['천문학', '과학사'])
        self.assertEqual(
            _build_user_profile(self.user)['interests'],
            ['천문학', '과학사'],
        )

    def test_profile_rejects_fewer_than_three_total_preferences(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            '/api/myprofile/profile/',
            {'profile': {'interests': ['음악'], 'hobbies': []}},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('preferences', response.data)

    def test_profile_allows_more_than_three_in_one_category(self):
        self.client.force_authenticate(self.user)

        response = self.client.put(
            '/api/myprofile/profile/',
            {
                'profile': {
                    'interests': ['음악', '여행', '사진', '천문학'],
                    'hobbies': [],
                }
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(
            self.profile.interests,
            ['음악', '여행', '사진', '천문학'],
        )
        self.assertEqual(self.profile.hobbies, [])
