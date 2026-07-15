from django.conf import settings
from django.db import models


STYLE_PRESET_CHOICES = [
    ('ANIME', '감성 애니메이션'),
    ('WARM_CARTOON', '따뜻한 카툰'),
    ('RENDER_3D', '3D 렌더'),
    ('CLAY_3D', '클레이 3D'),
    ('WATERCOLOR', '수채화'),
    ('OIL', '유화'),
    ('PENCIL', '색연필'),
    ('OIL_PASTEL', '오일파스텔'),
    ('PIXEL', '픽셀 아트'),
    ('FLAT', '플랫 일러스트'),
    ('STORYBOOK', '동화책 삽화'),
    ('MONO', '흑백 드로잉'),
]


class MyCard(models.Model):
    SKY_CHOICES = [
        ('CLEAR', '맑음'), ('SUNSET', '노을'), ('CLOUDY', '흐림'),
        ('RAIN', '비'), ('STARRY', '별이 많은 밤'),
    ]
    PACE_CHOICES = [
        ('SLOW', '천천히'), ('NORMAL', '평소대로'), ('RUSH', '정신없이'),
        ('STILL', '멈춰 있고 싶음'),
    ]
    SPACE_CHOICES = [
        ('BED', '침대'), ('CAFE', '카페'), ('FOREST', '숲'),
        ('SEA', '바다'), ('STREET', '사람 많은 거리'),
    ]
    PHRASE_CHOICES = [
        ('ENDURED', '잘 버텼어'), ('TIRED', '조금 지쳤어'),
        ('OKAY', '꽤 괜찮았어'), ('COMPLICATED', '복잡했어'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='my_cards')
    date = models.DateField(db_index=True)
    sky = models.CharField(max_length=16, choices=SKY_CHOICES)
    pace = models.CharField(max_length=16, choices=PACE_CHOICES)
    space = models.CharField(max_length=16, choices=SPACE_CHOICES)
    phrase = models.CharField(max_length=16, choices=PHRASE_CHOICES)
    free_text = models.CharField(max_length=200, blank=True, default='')
    style = models.CharField(max_length=32, blank=True, default='')
    custom_style = models.CharField(max_length=100, blank=True, default='')
    image_url = models.URLField(blank=True, default='')
    title = models.CharField(max_length=60, blank=True, default='')
    description = models.CharField(max_length=200, blank=True, default='')
    is_saved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'date'], name='mycard_user_date_idx')]
