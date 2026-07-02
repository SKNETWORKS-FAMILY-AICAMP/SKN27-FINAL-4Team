from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='character',
            field=models.CharField(
                blank=True,
                choices=[
                    ('sodam', '소담'),
                    ('bandi', '반디'),
                    ('geuru', '그루'),
                    ('tori', '토리'),
                ],
                max_length=10,
            ),
        ),
    ]
