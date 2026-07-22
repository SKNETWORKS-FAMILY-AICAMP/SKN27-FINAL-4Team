# 👍👎 피드백/MLOps 재학습 큐 제거 — 2차 확장에서 Feedback Agent와 함께 재설계 예정

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0011_delete_bookcuration'),
    ]

    operations = [
        migrations.DeleteModel(
            name='MlopsQueue',
        ),
    ]
