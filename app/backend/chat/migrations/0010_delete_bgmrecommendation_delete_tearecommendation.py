# 차/BGM 추천 기능 제거 (v6.0 스코프 정리)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0009_usermemory_chatsession_cold_start_done_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BgmRecommendation',
        ),
        migrations.DeleteModel(
            name='TeaRecommendation',
        ),
    ]
