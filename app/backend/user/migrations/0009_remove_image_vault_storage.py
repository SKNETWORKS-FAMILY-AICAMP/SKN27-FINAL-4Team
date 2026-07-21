from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("user", "0008_useragreementrecord"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS saved_card_images;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
