# Generated manually for myprofile API integration.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30)),
                ('mbti', models.CharField(max_length=4)),
                ('gender', models.CharField(max_length=20)),
                ('age', models.PositiveSmallIntegerField()),
                ('birthday', models.CharField(max_length=20)),
                ('job', models.CharField(max_length=80)),
                ('status', models.CharField(max_length=80)),
                ('keywords', models.CharField(max_length=255)),
                ('interests', models.JSONField(default=list)),
                ('hobbies', models.CharField(max_length=80)),
                ('selected_character', models.CharField(default='sol', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='myprofile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_profiles',
            },
        ),
    ]
