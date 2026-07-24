from rest_framework import serializers

from .constants import (
    normalize_mypage_character_id,
    normalize_preference_labels,
)

class MyProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    job = serializers.CharField(max_length=100, required=False, allow_blank=True)
    birthDate = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    interests = serializers.ListField(child=serializers.CharField(), required=False)
    hobbies = serializers.ListField(child=serializers.CharField(), required=False)
    selectedCharacter = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def validate_interests(self, value):
        return normalize_preference_labels(value)

    def validate_hobbies(self, value):
        return normalize_preference_labels(value)

    def validate_selectedCharacter(self, value):
        if not value:
            return ''
        normalized = normalize_mypage_character_id(value)
        if not normalized:
            raise serializers.ValidationError('지원하지 않는 캐릭터입니다.')
        return normalized

    def to_representation(self, instance):
        user = instance.get('user')
        profile = instance.get('profile')

        birth_date_str = ""
        if profile and profile.birth_date:
            birth_date_str = profile.birth_date.strftime("%Y.%m.%d")

        selected_character = ''
        if user:
            preference = user.character_preferences.order_by('-updated_at').first()
            selected_character = normalize_mypage_character_id(
                preference.character_id if preference else user.character
            )

        return {
            'name': user.nickname if user else "",
            'job': profile.job if profile else "",
            'birthDate': birth_date_str,
            'gender': profile.gender if profile else "",
            'interests': profile.interests if profile else [],
            'hobbies': profile.hobbies if profile else [],
            'selectedCharacter': selected_character or 'otter',
            'account': {
                'email': user.email if user else "",
                'provider': user.oauth_accounts.first().provider.capitalize() if user and user.oauth_accounts.exists() else "Email",
                'joinedAt': user.created_at.strftime("%Y.%m.%d") if user else "",
                'lastLogin': user.last_login.strftime("%Y.%m.%d %H:%M") if user and user.last_login else "",
                'session': "현재 접속 중",
                'plan': "Free",
            } if user else None,
        }
