from rest_framework import serializers
from .models import UserScaleEstimate, ClinicalScale


class ClinicalScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicalScale
        fields = ['scale_id', 'scale_name_ko', 'domain', 'time_frame']


class UserScaleEstimateSerializer(serializers.ModelSerializer):
    scale = ClinicalScaleSerializer(read_only=True)

    class Meta:
        model = UserScaleEstimate
        fields = ['id', 'scale', 'estimated_score', 'target_date', 'calculated_at']
        read_only_fields = ['id', 'calculated_at']
