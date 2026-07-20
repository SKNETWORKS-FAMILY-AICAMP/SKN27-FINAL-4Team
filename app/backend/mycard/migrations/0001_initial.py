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
            name='MyCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('sky', models.CharField(choices=[('CLEAR', '맑음'), ('SUNSET', '노을'), ('CLOUDY', '흐림'), ('RAIN', '비'), ('STARRY', '별이 많은 밤')], max_length=16)),
                ('pace', models.CharField(choices=[('SLOW', '천천히'), ('NORMAL', '평소대로'), ('RUSH', '정신없이'), ('STILL', '멈춰 있고 싶음')], max_length=16)),
                ('space', models.CharField(choices=[('BED', '침대'), ('CAFE', '카페'), ('FOREST', '숲'), ('SEA', '바다'), ('STREET', '사람 많은 거리')], max_length=16)),
                ('phrase', models.CharField(choices=[('ENDURED', '잘 버텼어'), ('TIRED', '조금 지쳤어'), ('OKAY', '꽤 괜찮았어'), ('COMPLICATED', '복잡했어')], max_length=16)),
                ('free_text', models.CharField(blank=True, default='', max_length=200)),
                ('style', models.CharField(blank=True, default='', max_length=32)),
                ('custom_style', models.CharField(blank=True, default='', max_length=100)),
                ('image_url', models.URLField(blank=True, default='')),
                ('title', models.CharField(blank=True, default='', max_length=60)),
                ('description', models.CharField(blank=True, default='', max_length=200)),
                ('is_saved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='my_cards', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['user', 'date'], name='mycard_user_date_idx')],
            },
        ),
    ]
