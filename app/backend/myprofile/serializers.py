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
            # 더미 데이터 유지 (DB에 없지만 프론트엔드 에러 방지)
            'mbti': "INFP",
            'status': "교류하고 싶음",
            'keywords': "공감형, 느린 집중, 감성 기록, 안정 선호",
        }
