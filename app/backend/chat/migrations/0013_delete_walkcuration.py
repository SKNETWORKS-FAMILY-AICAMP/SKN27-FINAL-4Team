# 산책 큐레이션(plan-support 장소 추천) 기능 폐기로 제거 — 2026-07-05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0012_delete_mlopsqueue'),
    ]

    operations = [
        migrations.DeleteModel(
            name='WalkCuration',
        ),
    ]
