from django.db import migrations

# (행정코드, 이름, 영문명, 위도, 경도) — 좌표는 시·군청 부근 대략값
SIGUNGU = [
    ("44130", "천안시", "Cheonan", 36.8151, 127.1139),
    ("44150", "공주시", "Gongju", 36.4465, 127.1190),
    ("44180", "보령시", "Boryeong", 36.3334, 126.6129),
    ("44200", "아산시", "Asan", 36.7898, 127.0019),
    ("44210", "서산시", "Seosan", 36.7848, 126.4503),
    ("44230", "논산시", "Nonsan", 36.1872, 127.0987),
    ("44250", "계룡시", "Gyeryong", 36.2745, 127.2487),
    ("44270", "당진시", "Dangjin", 36.8930, 126.6475),
    ("44710", "금산군", "Geumsan", 36.1088, 127.4881),
    ("44760", "부여군", "Buyeo", 36.2756, 126.9097),
    ("44770", "서천군", "Seocheon", 36.0803, 126.6914),
    ("44790", "청양군", "Cheongyang", 36.4592, 126.8023),
    ("44800", "홍성군", "Hongseong", 36.6010, 126.6608),
    ("44810", "예산군", "Yesan", 36.6826, 126.8486),
    ("44825", "태안군", "Taean", 36.7456, 126.2980),
]


def seed(apps, schema_editor):
    Region = apps.get_model("core", "Region")
    sido, _ = Region.objects.get_or_create(
        code="44",
        defaults=dict(name="충청남도", name_en="Chungcheongnam-do", level="sido", lat=36.5184, lng=126.8000),
    )
    for code, name, name_en, lat, lng in SIGUNGU:
        Region.objects.get_or_create(
            code=code,
            defaults=dict(name=name, name_en=name_en, level="sigungu", parent=sido, lat=lat, lng=lng),
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
