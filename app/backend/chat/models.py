from django.db import models
from django.conf import settings
# NOTE: v6.0 — 캐릭터 4종(포리·까미·토토·여울), UserMemory/MbtiAnswer 추가


class ChatSession(models.Model):
    CHARACTER_CHOICES = [
        ('pori',  '포리'),   # 레서판다 / 밝음·응원형
        ('kkami', '까미'),   # 고양이 / 깊음·묵직형
        ('toto',  '토토'),   # 수달 / 장난·환기형
        ('yeoul', '여울'),   # 뱁새 / 차분·포근형
    ]
    EMOTION4_CHOICES = [
        ('joy', '기쁨'),
        ('sadness', '슬픔'),
        ('anger', '분노'),
        ('normal', '일반'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True,
    )
    character = models.CharField(max_length=10, choices=CHARACTER_CHOICES, default='pori')
    is_secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # ── 콜드스타트 게이팅 (최종_통합_흐름도 §1) ──
    cold_start_done = models.BooleanField(default=False, verbose_name='감정 선택 질문 답변 완료')
    selected_emotion = models.CharField(
        max_length=10, choices=EMOTION4_CHOICES, blank=True, null=True,
        verbose_name='콜드스타트에서 선택한 초기 감정',
    )

    # ── MBTI 서브플로우 상태 (최종_통합_흐름도 §5) ──
    mbti_pending = models.BooleanField(default=False, verbose_name='MBTI 질문 pending 플래그')
    mbti_last_question_code = models.CharField(max_length=20, blank=True, null=True)
    mbti_candidate_answer = models.TextField(
        blank=True, null=True,
        verbose_name='시크릿 모드에서 저장 동의 대기 중인 MBTI 답변',
    )

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.character}] {self.user} ({self.created_at:%Y-%m-%d})'


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    EMOTION4_CHOICES = [  # 4감정 (분류·표정·TTS·추천 단위) — v5.3
        ('joy', '기쁨'),
        ('sadness', '슬픔'),
        ('anger', '분노'),
        ('normal', '일반'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    emotion_label = models.CharField(max_length=20, choices=EMOTION4_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']


# (WalkCuration(산책 큐레이션)은 장소 추천 기능 폐기로 제거 — 2026-07-05, 0013 마이그레이션)


# ── 장기 요약 메모리 (user_memory) ───────────────────────────
class UserMemory(models.Model):
    """오래된 대화를 LLM으로 압축한 장기 요약 (사용자당 1행).
    일반 모드 턴 종료 시 비동기 갱신되며, 컨텍스트 조회 시 최근 N턴 원문과 함께
    에이전트에 전달된다. (최종_통합_흐름도 §2 / ERD v6.0)"""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memory',
        primary_key=True,
    )
    summary_text = models.TextField(blank=True, default='', verbose_name='장기 요약')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_memory'
        verbose_name = '장기 요약 메모리'
        verbose_name_plural = '장기 요약 메모리 목록'

    def __str__(self):
        return f'memory({self.user_id})'


# ── MBTI 답변 수집 ───────────────────────────────────────────
class MbtiAnswer(models.Model):
    """유휴 타이머(10초) 기반 MBTI 질문에 대한 답변 수집 테이블.
    시크릿 모드에서는 사용자 동의 시에만 저장된다. (최종_통합_흐름도 §5)"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mbti_answers',
    )
    question_code = models.CharField(max_length=20, verbose_name='MBTI 유도 질문 코드')
    answer_text = models.TextField(verbose_name='사용자 답변 원문')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mbti_answers'
        ordering = ['-created_at']
        verbose_name = 'MBTI 답변'
        verbose_name_plural = 'MBTI 답변 목록'

    def __str__(self):
        return f'[{self.question_code}] {self.user_id}'


# (MlopsQueue — 👍👎 피드백/재학습 큐는 2차 확장으로 제거, 2026-07-02)
