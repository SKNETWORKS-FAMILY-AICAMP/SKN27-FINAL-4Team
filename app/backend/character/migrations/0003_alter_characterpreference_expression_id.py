from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("character", "0002_rename_character_c_user_id_71aa5c_idx_character_c_user_id_c8a965_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="characterpreference",
            name="expression_id",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("joy", "Joy"),
                    ("anger", "Anger"),
                    ("sadness", "Sadness"),
                    ("anxiety", "Anxiety"),
                    ("hurt", "Hurt"),
                    ("panic", "Panic"),
                ],
                default="default",
                max_length=24,
            ),
        ),
    ]
