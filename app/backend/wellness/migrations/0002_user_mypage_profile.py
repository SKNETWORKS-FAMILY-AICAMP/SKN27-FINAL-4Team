# Generated manually for feature-mypage backend integration.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wellness', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMypageProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_data', models.JSONField(blank=True, default=dict)),
                ('settings_data', models.JSONField(blank=True, default=dict)),
                ('selected_character', models.CharField(blank=True, default='sol', max_length=20)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='mypage_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_mypage_profiles',
            },
        ),
    ]
