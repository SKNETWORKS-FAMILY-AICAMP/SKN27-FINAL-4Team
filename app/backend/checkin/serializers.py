from rest_framework import serializers

from .models import (
    ActionFeedback,
    CauseOption,
    CheckinRecommendation,
    DailyCheckin,
    NeedOption,
    RecommendationAction,
    ReflectionOption,
)


class ReflectionOptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='reflection_id', read_only=True)

    class Meta:
        model = ReflectionOption
        fields = ['id', 'reflection_id', 'label', 'hint', 'icon', 'primary_emotion', 'secondary_emotion', 'emotion_intensity_default', 'state_tags', 'energy_level', 'cause_context', 'ack_key', 'next_stage', 'include_weekly', 'display_order']


class CauseOptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='cause_id', read_only=True)
    display_text = serializers.SerializerMethodField()

    class Meta:
        model = CauseOption
        fields = ['id', 'cause_id', 'cause_code', 'label', 'hint', 'icon', 'available_contexts', 'option_text_neutral', 'option_text_positive', 'option_text_difficult', 'option_text_mixed', 'display_text', 'display_order']

    def get_display_text(self, obj):
        return obj.label


class NeedOptionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='need_id', read_only=True)

    class Meta:
        model = NeedOption
        fields = ['id', 'need_id', 'need_code', 'label', 'hint', 'icon', 'response_mode', 'display_order']


class RecommendationActionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='action_id', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = RecommendationAction
        fields = ['id', 'action_id', 'title', 'description', 'expected_minutes', 'duration', 'icon', 'tags', 'safety_notice']

    def get_duration(self, obj):
        return f'{obj.expected_minutes}분'


class CheckinRecommendationSerializer(serializers.ModelSerializer):
    action = RecommendationActionSerializer(read_only=True)

    class Meta:
        model = CheckinRecommendation
        fields = ['action', 'score', 'rank', 'reason_codes', 'selected']


class ActionFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionFeedback
        fields = ['action', 'completed', 'helpfulness', 'feedback_at']


class DailyCheckinSerializer(serializers.ModelSerializer):
    reflection = ReflectionOptionSerializer(read_only=True)
    cause = CauseOptionSerializer(read_only=True)
    need = NeedOptionSerializer(read_only=True)
    selected_action = RecommendationActionSerializer(read_only=True)

    class Meta:
        model = DailyCheckin
        fields = [
            'id', 'checkin_date', 'stage', 'reflection', 'primary_emotion', 'secondary_emotion',
            'state_tags', 'energy_level', 'cause_context', 'cause_display_text_snapshot', 'cause', 'need', 'selected_action', 'final_route',
            'character_id', 'character_snapshot', 'completed_at', 'created_at', 'updated_at',
        ]
