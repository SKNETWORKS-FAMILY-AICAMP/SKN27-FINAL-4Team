"""
기능: 마음 리포트(Mind Report)의 결과물(감정 일기, 키워드, 분석 문장 등)을 DB에 저장하기 위한 데이터베이스 테이블 구조(Schema)를 정의하는 파일입니다.
"""
from django.db import models
from django.conf import settings
class MindReport(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mind_reports'
    )
    report_type = models.CharField(max_length=50) # "주간 (데이터 부족)" 등
    range_text = models.CharField(max_length=100) # "이번 주" 등
    title = models.CharField(max_length=200)
    summary = models.TextField()
    stress_causes = models.JSONField(default=list)
    relief_causes = models.JSONField(default=list)
    cause_labels = models.JSONField(default=list)
    emotions = models.JSONField(default=list)
    analysis = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    is_fallback = models.BooleanField(default=False)
    is_safety_response = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mind_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.nickname} - {self.title} ({self.created_at.strftime('%Y-%m-%d')})"



