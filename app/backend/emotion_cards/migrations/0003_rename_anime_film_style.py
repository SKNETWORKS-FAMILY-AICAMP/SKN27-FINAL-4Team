from django.db import migrations


def rename_anime_film_style(apps, schema_editor):
    CatalogEntry = apps.get_model('emotion_cards', 'CatalogEntry')
    CatalogEntry.objects.filter(
        catalog='style',
        code='STYLE_ANIME_FILM',
    ).update(display_name='지브리')


def restore_anime_film_style(apps, schema_editor):
    CatalogEntry = apps.get_model('emotion_cards', 'CatalogEntry')
    CatalogEntry.objects.filter(
        catalog='style',
        code='STYLE_ANIME_FILM',
    ).update(display_name='손그림 애니메이션 영화풍')


class Migration(migrations.Migration):
    dependencies = [
        ('emotion_cards', '0002_emotioncardusagereset'),
    ]

    operations = [
        migrations.RunPython(rename_anime_film_style, restore_anime_film_style),
    ]
