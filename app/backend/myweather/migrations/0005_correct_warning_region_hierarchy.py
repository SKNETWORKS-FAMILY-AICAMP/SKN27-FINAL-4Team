from django.db import migrations


REGION_ALIASES = {
    "인천": [
        "인천광역시",
        "서해5도",
        "백령도",
        "대청도",
        "소청도",
        "연평도",
        "강화군 우도",
    ],
    "전남광주": [
        "전남광주통합특별시",
        "광주",
        "광주광역시",
        "전남",
        "전라남도",
        "흑산도",
        "홍도",
        "흑산도.홍도",
        "흑산도·홍도",
    ],
    "경북": [
        "경상북도",
        "울릉도",
        "독도",
        "울릉도.독도",
        "울릉도·독도",
    ],
}


def update_island_region_aliases(apps, schema_editor):
    WeatherRegion = apps.get_model("myweather", "WeatherRegion")
    for name, aliases in REGION_ALIASES.items():
        WeatherRegion.objects.filter(name=name).update(aliases=aliases)


def restore_previous_aliases(apps, schema_editor):
    WeatherRegion = apps.get_model("myweather", "WeatherRegion")
    previous = {
        "인천": ["인천광역시"],
        "전남광주": [
            "전남광주통합특별시",
            "광주",
            "광주광역시",
            "전남",
            "전라남도",
        ],
        "경북": ["경상북도", "울릉도", "독도"],
    }
    for name, aliases in previous.items():
        WeatherRegion.objects.filter(name=name).update(aliases=aliases)


class Migration(migrations.Migration):
    dependencies = [("myweather", "0004_populate_phrasing_filters")]

    operations = [
        migrations.RunPython(update_island_region_aliases, restore_previous_aliases),
    ]
