from rest_framework import serializers

from .models import FeatureCode


class AnalysisRequestSerializer(serializers.Serializer):
    raw_text = serializers.CharField(max_length=500, required=False, allow_blank=True)
    emotion_text = serializers.CharField(max_length=500, required=False, allow_blank=True)
    event_text = serializers.CharField(max_length=500, required=False, allow_blank=True)
    energy_text = serializers.CharField(max_length=120, required=False, allow_blank=True)
    need_text = serializers.CharField(max_length=120, required=False, allow_blank=True)
    memory_text = serializers.CharField(max_length=500, required=False, allow_blank=True)
    explicit_place = serializers.CharField(max_length=80, required=False, allow_blank=True)
    energy_code = serializers.CharField(max_length=80, required=False, allow_blank=True)
    need_code = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate(self, attrs):
        if not any(attrs.get(key, '').strip() for key in ('raw_text', 'emotion_text', 'event_text', 'memory_text')):
            raise serializers.ValidationError('오늘의 감정이나 기억을 한 줄 이상 적어주세요.')
        if attrs.get('raw_text') and not attrs.get('emotion_text'):
            attrs['emotion_text'] = attrs['raw_text']
        for field, group in (('energy_code', 'ENERGY'), ('need_code', 'NEED')):
            value = attrs.get(field)
            if value and not FeatureCode.objects.filter(group=group, code=value).exists():
                raise serializers.ValidationError({field: '지원하지 않는 선택 값입니다.'})
        return attrs


class AnalysisPatchSerializer(serializers.Serializer):
    primary_emotion = serializers.CharField(max_length=80, required=False)
    energy_code = serializers.CharField(max_length=80, required=False)
    need_code = serializers.CharField(max_length=80, required=False)
    memory_focus = serializers.CharField(max_length=200, required=False, allow_blank=True)

    def validate(self, attrs):
        checks = (('primary_emotion', 'PRIMARY_EMOTION'), ('energy_code', 'ENERGY'), ('need_code', 'NEED'))
        for field, group in checks:
            value = attrs.get(field)
            if value and not FeatureCode.objects.filter(group=group, code=value).exists():
                raise serializers.ValidationError({field: '지원하지 않는 선택 값입니다.'})
        return attrs


class GenerationSerializer(serializers.Serializer):
    style_id = serializers.CharField(max_length=100)
    idempotency_key = serializers.CharField(max_length=100, required=False, allow_blank=True)


class FeedbackSerializer(serializers.Serializer):
    helpful = serializers.BooleanField(required=False)
    want_similar = serializers.BooleanField(required=False)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)
