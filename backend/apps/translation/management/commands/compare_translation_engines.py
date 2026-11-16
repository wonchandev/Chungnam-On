import json
import re
from collections import Counter
from time import monotonic

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.translation.backends import GoogleTranslator, OpenAITranslator
from apps.translation.errors import TranslationProviderError


SAMPLES = (
    {
        "id": "pay_and_break",
        "source": "일당은 120,000원이고 휴게시간은 30분입니다.",
        "reference": "The daily pay is 120,000 won, and the break is 30 minutes.",
        "terms": (("daily pay", "daily wage", "day rate"), ("break", "rest period")),
    },
    {
        "id": "head_protection",
        "source": "안전모를 착용한 뒤 작업장에 들어오세요.",
        "reference": "Please put on a hard hat before entering the work area.",
        "terms": (("hard hat", "safety helmet"),),
    },
    {
        "id": "arrival",
        "source": "작업 시작 10분 전까지 현장에 도착해 주세요.",
        "reference": "Please arrive on site 10 minutes before work starts.",
        "terms": (("before", "early"),),
    },
    {
        "id": "schedule",
        "source": "오전 8시부터 오후 5시까지 근무합니다.",
        "reference": "Working hours are from 8 a.m. to 5 p.m.",
        "terms": (("a.m.", "am", "morning"), ("p.m.", "pm", "afternoon")),
    },
)
NUMBER_PATTERN = re.compile(r"\d+(?:[, \u00a0]\d{3})*(?:\.\d+)?")


def numbers(text: str) -> Counter:
    return Counter(re.sub(r"[, \u00a0]", "", value) for value in NUMBER_PATTERN.findall(text))


def score(sample: dict, translation: str) -> dict:
    return {
        "numbers_preserved": numbers(sample["source"]) == numbers(translation),
        "terms_found": sum(
            any(re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", translation, re.I) for term in variants)
            for variants in sample["terms"]
        ),
        "terms_total": len(sample["terms"]),
    }


class Command(BaseCommand):
    help = "같은 한국어 현장 문장에 대한 Google·OpenAI 번역과 수치·용어 검사를 출력한다."

    def add_arguments(self, parser):
        parser.add_argument("--provider", choices=["both", "google", "openai"], default="both")

    def handle(self, *args, **options):
        providers = {
            "google": (settings.GOOGLE_TRANSLATE_API_KEY, GoogleTranslator),
            "openai": (settings.OPENAI_API_KEY, OpenAITranslator),
        }
        selected = providers if options["provider"] == "both" else [options["provider"]]
        report = {"source": "ko", "target": "en", "providers": {}}
        for provider in selected:
            key, create_translator = providers[provider]
            if not key:
                report["providers"][provider] = {"status": "missing_key"}
                continue
            started = monotonic()
            try:
                translated = create_translator().translate_batch([s["source"] for s in SAMPLES], "ko", "en")
                if len(translated) != len(SAMPLES) or any(not isinstance(t, str) or not t.strip() for t in translated):
                    raise TranslationProviderError("translation_invalid_response")
            except TranslationProviderError as error:
                report["providers"][provider] = {"status": "error", "code": error.get_codes()}
                continue
            report["providers"][provider] = {
                "status": "ok",
                "elapsed_ms": round((monotonic() - started) * 1000),
                "samples": [
                    {"id": sample["id"], "source": sample["source"], "reference": sample["reference"],
                     "translation": result, **score(sample, result)}
                    for sample, result in zip(SAMPLES, translated, strict=True)
                ],
            }
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
