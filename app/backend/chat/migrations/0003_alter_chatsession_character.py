from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_alter_chatsession_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatsession',
            name='character',
            field=models.CharField(
                choices=[
                    ('sodam', '소담'),
                    ('bandi', '반디'),
                    ('geuru', '그루'),
                    ('tori', '토리'),
                ],
                default='sodam',
                max_length=10,
            ),
        ),
    ]
