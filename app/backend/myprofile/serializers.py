from rest_framework import serializers

from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'email',
            'name',
            'mbti',
            'gender',
            'age',
            'birthday',
            'job',
            'status',
            'keywords',
            'interests',
            'hobbies',
            'selected_character',
            'updated_at',
        ]
        read_only_fields = ['email', 'updated_at']

    def validate_mbti(self, value):
        value = value.strip().upper()
        valid_types = {
            'ISTJ', 'ISFJ', 'INFJ', 'INTJ',
            'ISTP', 'ISFP', 'INFP', 'INTP',
            'ESTP', 'ESFP', 'ENFP', 'ENTP',
            'ESTJ', 'ESFJ', 'ENFJ', 'ENTJ',
        }
        if value not in valid_types:
            raise serializers.ValidationError('Enter a valid MBTI type.')
        return value

    def validate_age(self, value):
        if value < 14 or value > 99:
            raise serializers.ValidationError('Age must be between 14 and 99.')
        return value

    def validate_interests(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError('Select at least one interest keyword.')
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError('Empty interest keywords cannot be saved.')
        return [item.strip() for item in value]

    def validate_selected_character(self, value):
        value = value.strip()
        valid_characters = {'sol', 'luna', 'on', 'nari'}
        if value not in valid_characters:
            raise serializers.ValidationError('Select a valid character.')
        return value

    def validate(self, attrs):
        required_text_fields = [
            'name',
            'gender',
            'birthday',
            'job',
            'status',
            'keywords',
            'hobbies',
            'selected_character',
        ]
        for field in required_text_fields:
            value = attrs.get(field)
            if not isinstance(value, str) or not value.strip():
                raise serializers.ValidationError({field: 'This field is required.'})
            attrs[field] = value.strip()
        return attrs
