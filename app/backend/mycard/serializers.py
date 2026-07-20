from rest_framework import serializers

from .models import MyCard, STYLE_PRESET_CHOICES


class MyCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyCard
        fields = ('id', 'image_url', 'title', 'description', 'is_saved')


class MyCardGenerateSerializer(serializers.Serializer):
    sky = serializers.ChoiceField(choices=[value for value, _ in MyCard.SKY_CHOICES])
    pace = serializers.ChoiceField(choices=[value for value, _ in MyCard.PACE_CHOICES])
    space = serializers.ChoiceField(choices=[value for value, _ in MyCard.SPACE_CHOICES])
    phrase = serializers.ChoiceField(choices=[value for value, _ in MyCard.PHRASE_CHOICES])
    free_text = serializers.CharField(required=False, allow_blank=True, max_length=200, default='')
    style = serializers.ChoiceField(choices=[value for value, _ in STYLE_PRESET_CHOICES], required=False, allow_blank=True, default='')
    custom_style = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100, default='')

    def validate(self, attrs):
        attrs['custom_style'] = (attrs.get('custom_style') or '').strip()
        attrs['style'] = (attrs.get('style') or '').strip()
        if not attrs['style'] and not attrs['custom_style']:
            raise serializers.ValidationError({'style': 'style 또는 custom_style 중 하나는 필요합니다.'})
        return attrs
