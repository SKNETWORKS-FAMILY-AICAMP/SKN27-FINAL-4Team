"""
기능: 마음 리포트(Mind Report)의 결과물(감정 일기, 키워드, 분석 문장 등)을 DB에 저장하기 위한 데이터베이스 테이블 구조(Schema)를 정의하는 파일입니다.
"""
from django.db import models
from django.conf import settings
from pgvector.django import VectorField

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
    emotions = models.JSONField(default=list)
    analysis = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    is_fallback = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'mind_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.nickname} - {self.title} ({self.created_at.strftime('%Y-%m-%d')})"


class WellnessKnowledge(models.Model):
    title = models.CharField(max_length=200, help_text="가이드 소스 문서 제목")
    content = models.TextField(help_text="지식 청크 텍스트")
    page_number = models.IntegerField(null=True, blank=True, help_text="원본 PDF 페이지 번호")
    
    # 1536차원의 OpenAI text-embedding-3-small 임베딩 벡터 저장 필드
    embedding = VectorField(dimensions=1536)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wellness_knowledge_base'

    def __str__(self):
        return f"[{self.title}] Page {self.page_number} - {self.content[:30]}..."

