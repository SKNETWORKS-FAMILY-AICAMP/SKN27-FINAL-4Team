from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_alter_chatsession_character'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='emotion6',
            field=models.CharField(
                blank=True,
                null=True,
                max_length=20,
                choices=[
                    ('anger', '분노'),
                    ('sadness', '슬픔'),
                    ('anxiety', '불안'),
                    ('hurt', '상처'),
                    ('fluster', '당황'),
                    ('joy', '기쁨'),
                ],
            ),
        ),
    ]
