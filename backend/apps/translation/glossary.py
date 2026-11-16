"""한국어 공고·채팅에서 일관되게 번역할 현장 용어."""

import re


DAILY_PAY = {
    "en": "daily pay", "vi": "tiền công theo ngày", "th": "ค่าจ้างรายวัน", "zh": "日薪",
    "uz": "kunlik ish haqi", "km": "ប្រាក់ឈ្នួលប្រចាំថ្ងៃ", "ne": "दैनिक ज्याला",
    "id": "upah harian", "mn": "өдрийн цалин",
}
TERMS = {
    "일당": DAILY_PAY,
    "일급": DAILY_PAY,
    "시급": {
        "en": "hourly pay", "vi": "tiền công theo giờ", "th": "ค่าจ้างรายชั่วโมง", "zh": "时薪",
        "uz": "soatlik ish haqi", "km": "ប្រាក់ឈ្នួលតាមម៉ោង", "ne": "प्रतिघण्टा ज्याला",
        "id": "upah per jam", "mn": "цагийн цалин",
    },
    "4대보험": {
        "en": "four major social insurance programs", "vi": "bốn loại bảo hiểm xã hội chính",
        "th": "การประกันสังคมหลัก 4 ประเภท", "zh": "四大社会保险", "uz": "to‘rtta asosiy ijtimoiy sug‘urta turi",
        "km": "ការធានារ៉ាប់រងសង្គមសំខាន់ៗទាំងបួន", "ne": "चार प्रमुख सामाजिक बीमा कार्यक्रम",
        "id": "empat program asuransi sosial utama", "mn": "нийгмийн даатгалын үндсэн дөрвөн төрөл",
    },
    "안전모": {
        "en": "hard hat", "vi": "mũ bảo hộ", "th": "หมวกนิรภัย", "zh": "安全帽",
        "uz": "himoya kaskasi", "km": "មួកសុវត្ថិភាព", "ne": "सुरक्षा हेलमेट",
        "id": "helm keselamatan", "mn": "хамгаалалтын дуулга",
    },
    "휴게시간": {
        "en": "break time", "vi": "thời gian nghỉ giải lao", "th": "เวลาพัก", "zh": "休息时间",
        "uz": "dam olish vaqti", "km": "ម៉ោងសម្រាក", "ne": "विश्राम समय",
        "id": "waktu istirahat", "mn": "амралтын цаг",
    },
}
TERM_PATTERN = re.compile(r"(?<![가-힣])(?:4대[ \t]*보험|휴게[ \t]*시간|안전모|일당|일급|시급)")


def mark_terms(text: str, target: str) -> tuple[str, dict[str, str]]:
    """번역문에서 고정 번역어로 복원할 용어의 위치를 표시한다."""
    prefix = "CHUNGNAMTERM"
    while prefix in text:
        prefix += "X"

    replacements = {}

    def mark(match):
        term = "".join(match[0].split())
        translation = TERMS[term].get(target)
        if translation is None:
            return match[0]
        marker = f"{prefix}{len(replacements)}X"
        replacements[marker] = translation
        return marker

    return TERM_PATTERN.sub(mark, text), replacements


def restore_terms(text: str, replacements: dict[str, str]) -> str:
    for marker, term in replacements.items():
        if text.count(marker) != 1:
            raise ValueError("Translation did not preserve a glossary marker")
        text = text.replace(marker, term)
    return text
