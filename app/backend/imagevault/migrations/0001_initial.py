import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SavedCardImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("image_url", models.TextField()),
                ("thumbnail_url", models.TextField(blank=True)),
                ("source", models.CharField(blank=True, max_length=40)),
                ("source_id", models.CharField(blank=True, max_length=120)),
                ("description", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_card_images", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "saved_card_images",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.AddIndex(
            model_name="savedcardimage",
            index=models.Index(fields=["user", "created_at"], name="saved_card_user_created_idx"),
        ),
    ]
