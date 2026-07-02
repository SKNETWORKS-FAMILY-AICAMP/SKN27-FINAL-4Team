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
            name='DailyTarotFortune',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_id', models.CharField(blank=True, db_index=True, max_length=64)),
                ('target_date', models.DateField(db_index=True)),
                ('fortune_type', models.CharField(default='daily_major', max_length=30)),
                ('birth_number', models.PositiveSmallIntegerField()),
                ('date_number', models.PositiveSmallIntegerField()),
                ('daily_number', models.PositiveSmallIntegerField()),
                ('card_number', models.IntegerField(db_index=True)),
                ('card_name', models.CharField(max_length=100)),
                ('card_name_ko', models.CharField(blank=True, max_length=100)),
                ('title', models.CharField(default='오늘의 메이저 카드', max_length=120)),
                ('message', models.TextField(blank=True)),
                ('source', models.CharField(choices=[('rule', 'Rule'), ('llm', 'LLM'), ('hybrid', 'Hybrid')], default='rule', max_length=30)),
                ('model_name', models.CharField(blank=True, max_length=100)),
                ('prompt_version', models.CharField(blank=True, max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='daily_tarot_fortunes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'daily_tarot_fortunes',
                'ordering': ['-target_date', '-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='dailytarotfortune',
            index=models.Index(fields=['user', 'target_date', 'fortune_type'], name='daily_tarot_user_id_910d58_idx'),
        ),
        migrations.AddIndex(
            model_name='dailytarotfortune',
            index=models.Index(fields=['client_id', 'target_date', 'fortune_type'], name='daily_tarot_client__57459d_idx'),
        ),
        migrations.AddIndex(
            model_name='dailytarotfortune',
            index=models.Index(fields=['card_number', 'target_date'], name='daily_tarot_card_nu_0e62a0_idx'),
        ),
        migrations.AddConstraint(
            model_name='dailytarotfortune',
            constraint=models.UniqueConstraint(condition=models.Q(('user__isnull', False)), fields=('user', 'target_date', 'fortune_type'), name='uniq_daily_tarot_user_date_type'),
        ),
        migrations.AddConstraint(
            model_name='dailytarotfortune',
            constraint=models.UniqueConstraint(condition=models.Q(('client_id__gt', '')), fields=('client_id', 'target_date', 'fortune_type'), name='uniq_daily_tarot_client_date_type'),
        ),
    ]
