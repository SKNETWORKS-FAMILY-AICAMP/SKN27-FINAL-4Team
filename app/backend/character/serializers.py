from rest_framework import serializers

from .models import CharacterPreference


class CharacterPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharacterPreference
        fields = [
            'id',
            'character_id',
            'expression_id',
            'created_at',
            'updated_at',
        ]

