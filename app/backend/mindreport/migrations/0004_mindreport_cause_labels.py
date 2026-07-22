from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('mindreport', '0003_sanitize_legacy_fallback_reports'),
    ]

    operations = [
        migrations.AddField(
            model_name='mindreport',
            name='cause_labels',
            field=models.JSONField(default=list),
        ),
    ]
