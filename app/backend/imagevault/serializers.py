from rest_framework import serializers

from .models import SavedCardImage


class SavedCardImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedCardImage
        fields = [
            "id",
            "name",
            "image_url",
            "thumbnail_url",
            "source",
            "source_id",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        cleaned = str(value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("이미지 이름을 입력해 주세요.")
        return cleaned

    def validate_image_url(self, value):
        cleaned = str(value or "").strip()
        if not cleaned:
            raise serializers.ValidationError("이미지 주소가 필요합니다.")
        return cleaned
