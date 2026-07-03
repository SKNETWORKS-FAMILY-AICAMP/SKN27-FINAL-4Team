from django.db import migrations, models


# v5.3 확정안: 6감정 → 4감정(기쁨/슬픔/분노/일반)
EMOTION4 = [
    ('joy', '기쁨'),
    ('sadness', '슬픔'),
    ('anger', '분노'),
    ('normal', '일반'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0006_bookcuration_walkcuration_alter_bgmrecommendation_id_and_more'),
    ]

    operations = [
        # ChatMessage: emotion6 컬럼 제거, emotion_label을 4감정으로
        migrations.RemoveField(
            model_name='chatmessage',
            name='emotion6',
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='emotion_label',
            field=models.CharField(blank=True, choices=EMOTION4, max_length=20, null=True),
        ),
        # 룰베이스 추천 마스터: emotion choices 4감정으로 정렬
        migrations.AlterField(
            model_name='tearecommendation',
            name='emotion',
            field=models.CharField(choices=EMOTION4, max_length=10, unique=True, verbose_name='감정 코드'),
        ),
        migrations.AlterField(
            model_name='bgmrecommendation',
            name='emotion',
            field=models.CharField(choices=EMOTION4, max_length=10, verbose_name='감정 코드'),
        ),
        migrations.AlterField(
            model_name='bookcuration',
            name='emotion',
            field=models.CharField(choices=EMOTION4, max_length=10, verbose_name='감정 코드'),
        ),
        migrations.AlterField(
            model_name='walkcuration',
            name='emotion',
            field=models.CharField(choices=EMOTION4, max_length=10, verbose_name='감정 코드'),
        ),
    ]
