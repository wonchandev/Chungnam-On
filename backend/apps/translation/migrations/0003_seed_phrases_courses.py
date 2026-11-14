from django.db import migrations

PHRASES = {
    "greeting": ["안녕하세요", "감사합니다", "죄송합니다", "네, 알겠습니다", "잘 모르겠습니다. 다시 설명해 주세요", "천천히 말씀해 주세요"],
    "work": ["오늘 무슨 일을 하나요?", "어디서 일하면 되나요?", "이렇게 하면 되나요?", "다 끝났습니다", "도와주세요", "잠깐 쉬어도 되나요?"],
    "safety": ["안전모를 착용하세요", "위험합니다. 조심하세요", "여기에 들어가면 안 됩니다", "안전화를 신어야 합니까?"],
    "pay": ["일당은 얼마입니까?", "급여는 언제 받나요?", "점심은 제공되나요?", "몇 시에 끝나나요?", "내일도 일할 수 있나요?"],
    "emergency": ["몸이 아픕니다", "병원에 가야 합니다", "다쳤습니다. 도와주세요", "119에 전화해 주세요"],
    "tools": ["이 자재는 어디에 놓나요?", "장비 사용법을 알려 주세요", "이것을 옮기면 됩니까?"],
}
COURSES = [
    ("무료 한국어 교육", "하루 10분이면 배우는 한국어 수업. 부담없이 신청하세요", "ko", "class"),
    ("무료 영어 교육", "하루 10분이면 배우는 영어 수업. 부담없이 신청하세요", "en", "class"),
    ("말로 배우는 한국어", "화상통화로 배우는 말하기 중심 한국어", "ko", "video_call"),
]
QUICK = ["위치는 어디인가요?", "언제부터 근무 가능한가요?", "급여는 어떻게 되나요?", "사장님"]


def seed(apps, schema_editor):
    Phrase = apps.get_model("translation", "Phrase")
    LanguageCourse = apps.get_model("translation", "LanguageCourse")
    for cat, items in PHRASES.items():
        for i, text in enumerate(items):
            Phrase.objects.get_or_create(category=cat, text_ko=text, defaults={"order": i})
    for title, desc, lang, kind in COURSES:
        LanguageCourse.objects.get_or_create(title=title, defaults=dict(description=desc, taught_language=lang, kind=kind))
    QuickReply = apps.get_model("chat", "QuickReply")
    for i, text in enumerate(QUICK):
        QuickReply.objects.get_or_create(text_ko=text, defaults={"order": i})


class Migration(migrations.Migration):
    dependencies = [("translation", "0002_phrases_courses"), ("chat", "0002_quickreply_chatparticipant_left_at_message_image_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
