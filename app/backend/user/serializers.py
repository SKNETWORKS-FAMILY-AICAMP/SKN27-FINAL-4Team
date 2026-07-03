from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import UserProfile

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'nickname', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'nickname', 'character', 'onboarding_done', 'created_at']
        read_only_fields = ['email', 'created_at']


class UserPersonalProfileSerializer(serializers.ModelSerializer):
    nickname = serializers.CharField(source='user.nickname', read_only=True)
    agreements = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = UserProfile
        fields = [
            'nickname',
            'birth_date',
            'gender',
            'age',
            'job',
            'hobbies',
            'interests',
            'agreements',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_agreements(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('필수 약관 동의가 필요합니다.')

        if value.get('termsOfService') is not True or value.get('privacyCollection') is not True:
            raise serializers.ValidationError('필수 약관 동의가 필요합니다.')

        return value
