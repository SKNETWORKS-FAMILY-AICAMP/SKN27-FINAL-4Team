from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('user', '0003_userprofile_client_id'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='userprofile',
            name='uniq_user_profile_client_id',
        ),
        migrations.RemoveIndex(
            model_name='userprofile',
            name='user_profil_client__fd0b67_idx',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='client_id',
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL),
        ),
    ]
