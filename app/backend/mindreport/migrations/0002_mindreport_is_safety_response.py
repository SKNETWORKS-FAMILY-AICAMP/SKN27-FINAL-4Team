from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mindreport', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mindreport',
            name='is_safety_response',
            field=models.BooleanField(default=False),
        ),
    ]
