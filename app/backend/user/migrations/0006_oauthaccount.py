from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_userpreferencekeyword'),
    ]

    operations = [
        migrations.CreateModel(
            name='OAuthAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider', models.CharField(choices=[('kakao', 'Kakao'), ('naver', 'Naver'), ('google', 'Google')], max_length=20)),
                ('provider_user_id', models.CharField(max_length=191)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('raw_profile', models.JSONField(blank=True, default=dict)),
                ('connected_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='oauth_accounts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'oauth_accounts',
            },
        ),
        migrations.AddConstraint(
            model_name='oauthaccount',
            constraint=models.UniqueConstraint(fields=('provider', 'provider_user_id'), name='uniq_oauth_provider_user'),
        ),
        migrations.AddIndex(
            model_name='oauthaccount',
            index=models.Index(fields=['user', 'provider'], name='oauth_user_provider_idx'),
        ),
        migrations.AddIndex(
            model_name='oauthaccount',
            index=models.Index(fields=['provider', 'email'], name='oauth_provider_email_idx'),
        ),
    ]
