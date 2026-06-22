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
            name='ChatSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('character', models.CharField(
                    choices=[('haeon', '해온'), ('greung', '그릉'), ('dalkong', '달콩')],
                    default='haeon',
                    max_length=10,
                )),
                ('is_secret', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chat_sessions',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'chat_sessions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('user', 'User'), ('assistant', 'Assistant')],
                    max_length=10,
                )),
                ('content', models.TextField()),
                ('emotion_label', models.CharField(
                    blank=True,
                    choices=[('encourage', '응원'), ('sad', '속상'), ('angry', '화남'), ('plan', '계획')],
                    max_length=20,
                    null=True,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='messages',
                    to='chat.chatsession',
                )),
            ],
            options={
                'db_table': 'chat_messages',
                'ordering': ['created_at'],
            },
        ),
    ]
