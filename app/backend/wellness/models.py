from django.db import models
from django.conf import settings


class ClinicalScale(models.Model):
    scale_id = models.CharField(max_length=50, primary_key=True)  # e.g. 'PHQ-9', 'GAD-7'
    scale_name_ko = models.CharField(max_length=100)
    domain = models.CharField(max_length=50)                      # 'mental' or 'physical'
    time_frame = models.CharField(max_length=100, blank=True)     # e.g. '지난 2주'
    estimated_minutes = models.IntegerField(default=3)

    class Meta:
        db_table = 'clinical_scales'

    def __str__(self):
        return f'{self.scale_id} ({self.scale_name_ko})'


class ScaleQuestion(models.Model):
    question_id = models.CharField(max_length=50, primary_key=True)  # e.g. 'PHQ9_Q1'
    scale = models.ForeignKey(ClinicalScale, on_delete=models.CASCADE, related_name='questions')
    question_number = models.IntegerField()
    text = models.TextField()
    is_reverse = models.BooleanField(default=False)

    class Meta:
        db_table = 'scale_questions'


class ScaleOption(models.Model):
    scale = models.ForeignKey(ClinicalScale, on_delete=models.CASCADE, related_name='options')
    option_value = models.IntegerField()    # e.g. 0, 1, 2, 3
    option_label = models.CharField(max_length=100)  # e.g. '전혀 없음'

    class Meta:
        db_table = 'scale_options'


class UserScaleEstimate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scale_estimates')
    scale = models.ForeignKey(ClinicalScale, on_delete=models.CASCADE)
    estimated_score = models.DecimalField(max_digits=5, decimal_places=2)
    target_date = models.DateField()
    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_scale_estimates'
        ordering = ['-target_date']
