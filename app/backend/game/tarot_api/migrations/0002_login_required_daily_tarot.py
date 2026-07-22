from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tarot_api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='dailytarotfortune',
            name='uniq_daily_tarot_client_date_type',
        ),
        migrations.RemoveIndex(
            model_name='dailytarotfortune',
            name='daily_tarot_client__57459d_idx',
        ),
        migrations.RemoveField(
            model_name='dailytarotfortune',
            name='client_id',
        ),
        migrations.RemoveConstraint(
            model_name='dailytarotfortune',
            name='uniq_daily_tarot_user_date_type',
        ),
        migrations.AlterField(
            model_name='dailytarotfortune',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_tarot_fortunes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddConstraint(
            model_name='dailytarotfortune',
            constraint=models.UniqueConstraint(fields=('user', 'target_date', 'fortune_type'), name='uniq_daily_tarot_user_date_type'),
        ),
    ]
