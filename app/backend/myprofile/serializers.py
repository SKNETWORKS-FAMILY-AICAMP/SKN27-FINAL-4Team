from rest_framework import serializers

class MyProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    job = serializers.CharField(max_length=100, required=False, allow_blank=True)
    birthDate = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(max_length=20, required=False, allow_blank=True)
    interests = serializers.ListField(child=serializers.CharField(), required=False)
    hobbies = serializers.ListField(child=serializers.CharField(), required=False)
    selectedCharacter = serializers.CharField(max_length=10, required=False, allow_blank=True)

    def to_representation(self, instance):
        user = instance.get('user')
        profile = instance.get('profile')

        birth_date_str = ""
        if profile and profile.birth_date:
            birth_date_str = profile.birth_date.strftime("%Y.%m.%d")

        return {
            'name': user.nickname if user else "",
            'job': profile.job if profile else "",
            'birthDate': birth_date_str,
            'gender': profile.gender if profile else "",
            'interests': profile.interests if profile else [],
            'hobbies': profile.hobbies if profile else [],
            'selectedCharacter': user.character if user and user.character else "otter",
            'selectedCharacter': user.character if user and user.character else "otter",
            'account': {
                'email': user.email if user else "",
                'provider': user.oauth_accounts.first().provider.capitalize() if user and user.oauth_accounts.exists() else "Email",
                'joinedAt': user.created_at.strftime("%Y.%m.%d") if user else "",
                'lastLogin': user.last_login.strftime("%Y.%m.%d %H:%M") if user and user.last_login else "",
                'session': "현재 접속 중",
                'plan': "Free",
            } if user else None,
        }