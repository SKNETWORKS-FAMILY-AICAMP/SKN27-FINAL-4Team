from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0002_userprofile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='user',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='user.user'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='client_id',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddIndex(
            model_name='userprofile',
            index=models.Index(fields=['client_id', 'updated_at'], name='user_profil_client__fd0b67_idx'),
        ),
        migrations.AddConstraint(
            model_name='userprofile',
            constraint=models.UniqueConstraint(condition=models.Q(('client_id__gt', '')), fields=('client_id',), name='uniq_user_profile_client_id'),
        ),
    ]
