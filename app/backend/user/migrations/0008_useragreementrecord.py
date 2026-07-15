from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0007_merge_character_and_social'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserAgreementRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('terms_version', models.CharField(max_length=20)),
                ('privacy_version', models.CharField(max_length=20)),
                ('overseas_transfer_version', models.CharField(max_length=20)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('agreed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='agreement_records', to='user.user')),
            ],
            options={
                'db_table': 'user_agreement_records',
            },
        ),
        migrations.AddConstraint(
            model_name='useragreementrecord',
            constraint=models.UniqueConstraint(fields=('user', 'terms_version', 'privacy_version', 'overseas_transfer_version'), name='uniq_user_agreement_versions'),
        ),
        migrations.AddIndex(
            model_name='useragreementrecord',
            index=models.Index(fields=['user', '-agreed_at'], name='user_agreement_date_idx'),
        ),
    ]
