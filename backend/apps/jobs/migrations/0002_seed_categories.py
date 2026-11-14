from django.db import migrations

CATEGORIES = [
    ("manufacturing", "제조·생산", "Manufacturing"),
    ("construction", "건설현장", "Construction"),
    ("agriculture", "농업·축산", "Agriculture & Livestock"),
    ("logistics", "물류·배송", "Logistics & Delivery"),
    ("retail", "매장관리 및 판매", "Retail & Sales"),
    ("safety", "안전·경비", "Safety & Security"),
    ("food", "음식·서비스", "Food & Service"),
    ("etc", "기타", "Others"),
]


def seed(apps, schema_editor):
    JobCategory = apps.get_model("jobs", "JobCategory")
    for i, (code, name, name_en) in enumerate(CATEGORIES):
        JobCategory.objects.get_or_create(code=code, defaults=dict(name=name, name_en=name_en, order=i))


class Migration(migrations.Migration):
    dependencies = [("jobs", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
