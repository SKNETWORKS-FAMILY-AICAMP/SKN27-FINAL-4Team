from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_remove_userprofile_client_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserPreferenceKeyword',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keyword_type', models.CharField(choices=[('hobby', '취미'), ('interest', '관심분야')], max_length=20)),
                ('label', models.CharField(max_length=100)),
                ('source', models.CharField(default='onboarding', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preference_keywords', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_preference_keywords',
            },
        ),
        migrations.AddConstraint(
            model_name='userpreferencekeyword',
            constraint=models.UniqueConstraint(fields=('user', 'keyword_type', 'label'), name='uniq_user_preference_keyword'),
        ),
        migrations.AddIndex(
            model_name='userpreferencekeyword',
            index=models.Index(fields=['user', 'keyword_type'], name='user_pref_keyword_user_idx'),
        ),
        migrations.AddIndex(
            model_name='userpreferencekeyword',
            index=models.Index(fields=['keyword_type', 'label'], name='user_pref_keyword_label_idx'),
        ),
    ]
