from rest_framework import serializers

from .models import DailyFortune


class DailyFortuneSerializer(serializers.ModelSerializer):
    has_fortune = serializers.SerializerMethodField()

    class Meta:
        model = DailyFortune
        fields = [
            'id',
            'reading_id',
            'date',
            'topic',
            'title',
            'content',
            'keyword',
            'question',
            'cards',
            'category_results',
            'disclaimer',
            'has_fortune',
            'created_at',
            'updated_at',
        ]

    def get_has_fortune(self, obj):
        return bool(obj.content)

