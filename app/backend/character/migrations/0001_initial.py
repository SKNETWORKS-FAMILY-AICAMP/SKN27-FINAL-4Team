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
            name='CharacterPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('client_id', models.CharField(blank=True, db_index=True, max_length=64)),
                ('character_id', models.CharField(choices=[('otter', 'Otter'), ('cat', 'Cat'), ('redpanda', 'Red panda'), ('bird', 'Bird')], default='otter', max_length=24)),
                ('expression_id', models.CharField(choices=[('joy', 'Joy'), ('anger', 'Anger'), ('sadness', 'Sadness'), ('anxiety', 'Anxiety'), ('hurt', 'Hurt'), ('panic', 'Panic')], default='joy', max_length=24)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='character_preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='characterpreference',
            index=models.Index(fields=['user', 'updated_at'], name='character_c_user_id_71aa5c_idx'),
        ),
        migrations.AddIndex(
            model_name='characterpreference',
            index=models.Index(fields=['client_id', 'updated_at'], name='character_c_client__966619_idx'),
        ),
    ]
