from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from user.models import User, UserProfile
from mybook.views import _build_user_profile


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
        self.assertEqual(
            response.data['profile'],
            {
                'name': '청상아리',
                'job': '무직',
                'birthDate': '1997.03.25',
                'gender': '남',
                'interests': ['심리', '반려동물', '드라마', '디지털 트렌드'],
                'hobbies': ['음악 감상', '카페 투어', '산책'],
                'selectedCharacter': 'pori',
                'mbti': 'INFP',
                'status': '교류하고 싶음',
                'keywords': '공감형, 느린 집중, 감성 기록, 안정 선호',
            },
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
