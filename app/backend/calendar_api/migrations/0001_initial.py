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
            name='DailyFortune',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_id', models.CharField(blank=True, db_index=True, max_length=64)),
                ('reading_id', models.BigIntegerField(blank=True, db_index=True, null=True)),
                ('date', models.DateField(db_index=True)),
                ('topic', models.CharField(default='general', max_length=32)),
                ('title', models.CharField(default='Daily fortune', max_length=120)),
                ('content', models.TextField()),
                ('keyword', models.CharField(blank=True, max_length=80)),
                ('question', models.CharField(blank=True, max_length=500)),
                ('cards', models.JSONField(blank=True, default=list)),
                ('category_results', models.JSONField(blank=True, default=dict)),
                ('disclaimer', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='daily_fortunes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date', '-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='dailyfortune',
            index=models.Index(fields=['user', 'date'], name='calendar_ap_user_id_6d2f43_idx'),
        ),
        migrations.AddIndex(
            model_name='dailyfortune',
            index=models.Index(fields=['client_id', 'date'], name='calendar_ap_client__e126ba_idx'),
        ),
    ]
