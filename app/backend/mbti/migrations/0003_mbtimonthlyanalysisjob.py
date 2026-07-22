from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('mbti', '0002_remove_mbtimonthlyanalysisjob_monthly_result_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MbtiMonthlyAnalysisJob',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.BigIntegerField(db_index=True)),
                ('period_key', models.CharField(db_index=True, max_length=7)),
                ('status', models.CharField(choices=[('pending', 'pending'), ('running', 'running'), ('completed', 'completed'), ('skipped', 'skipped'), ('failed', 'failed')], db_index=True, default='pending', max_length=32)),
                ('trigger_source', models.CharField(choices=[('monthly_scheduler', 'monthly_scheduler'), ('dashboard_on_demand', 'dashboard_on_demand'), ('admin_retry', 'admin_retry'), ('manual', 'manual')], default='monthly_scheduler', max_length=32)),
                ('input_hash', models.CharField(db_index=True, max_length=64)),
                ('scoring_model', models.CharField(max_length=64)),
                ('prompt_version', models.CharField(max_length=64)),
                ('retry_count', models.PositiveIntegerField(default=0)),
                ('scheduled_at', models.DateTimeField(db_index=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('monthly_result', models.ForeignKey(blank=True, db_column='monthly_result_id', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='analysis_jobs', to='mbti.mbtimonthlyresultrecord')),
            ],
            options={
                'db_table': 'mbti_monthly_analysis_jobs',
                'ordering': ['scheduled_at', 'id'],
                'indexes': [
                    models.Index(fields=['status', 'scheduled_at'], name='mbti_monthl_status_b38b69_idx'),
                    models.Index(fields=['user_id', 'period_key'], name='mbti_monthl_user_id_63b490_idx'),
                    models.Index(fields=['user_id', 'period_key', 'input_hash'], name='mbti_monthl_user_id_338e9c_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('user_id', 'period_key', 'input_hash', 'prompt_version'), name='uniq_mbti_analysis_job_input_prompt'),
                ],
            },
        ),
    ]
