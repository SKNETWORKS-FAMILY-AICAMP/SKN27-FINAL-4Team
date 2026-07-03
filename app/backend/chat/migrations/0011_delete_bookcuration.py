# 도서 구절 큐레이션 기능 제거 (v6.0 스코프 정리 — 사용하는 API 없음)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0010_delete_bgmrecommendation_delete_tearecommendation'),
    ]

    operations = [
        migrations.DeleteModel(
            name='BookCuration',
        ),
    ]
