from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ConversationLog',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('user_id', models.BigIntegerField(db_index=True)),
                ('conversation_id', models.BigIntegerField(db_index=True)),
                ('role', models.CharField(db_index=True, max_length=20)),
                ('message_text', models.TextField()),
                ('created_at', models.DateTimeField(db_index=True)),
            ],
            options={
                'db_table': 'conversation_logs',
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='PreferenceEvidence',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('user_id', models.BigIntegerField(db_index=True)),
                ('message', models.ForeignKey(
                    db_column='message_id',
                    on_delete=django.db.models.deletion.DO_NOTHING,
                    related_name='preference_evidence',
                    to='taste.conversationlog',
                )),
                ('period_key', models.CharField(db_index=True, max_length=20)),
                ('normalized_keyword', models.CharField(db_index=True, max_length=100)),
                ('preference_type', models.CharField(db_index=True, max_length=50)),
                ('evidence_text', models.TextField()),
                ('conversation_context', models.TextField()),
                ('source_created_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'preference_evidence',
                'ordering': ['-source_created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='PreferenceKeywordSummary',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('user_id', models.BigIntegerField(db_index=True)),
                ('period_type', models.CharField(db_index=True, max_length=20)),
                ('period_key', models.CharField(db_index=True, max_length=20)),
                ('reflected_conversation_count', models.IntegerField(default=0)),
                ('reflected_message_count', models.IntegerField(default=0)),
                ('display_threshold', models.IntegerField(default=5)),
                ('keywords_json', models.TextField(blank=True, default='[]')),
                ('analyzed_at', models.DateTimeField(db_index=True)),
            ],
            options={
                'db_table': 'preference_keyword_summaries',
                'ordering': ['-analyzed_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='conversationlog',
            index=models.Index(fields=['user_id', 'role', 'created_at'], name='taste_conv_user_role_idx'),
        ),
        migrations.AddIndex(
            model_name='conversationlog',
            index=models.Index(fields=['conversation_id', 'created_at'], name='taste_conv_conv_idx'),
        ),
        migrations.AddIndex(
            model_name='preferenceevidence',
            index=models.Index(fields=['user_id', 'period_key', 'normalized_keyword'], name='taste_pref_ev_user_period_idx'),
        ),
        migrations.AddIndex(
            model_name='preferenceevidence',
            index=models.Index(fields=['user_id', 'preference_type', 'period_key'], name='taste_pref_ev_user_type_idx'),
        ),
        migrations.AddIndex(
            model_name='preferenceevidence',
            index=models.Index(fields=['message'], name='taste_pref_ev_msg_idx'),
        ),
        migrations.AddIndex(
            model_name='preferencekeywordsummary',
            index=models.Index(fields=['user_id', 'period_type', 'period_key'], name='taste_pref_kw_user_period_idx'),
        ),
        migrations.AddIndex(
            model_name='preferencekeywordsummary',
            index=models.Index(fields=['user_id', 'analyzed_at'], name='taste_pref_kw_user_analyzed_idx'),
        ),
    ]
