from itertools import chain

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.chat.models import QuickReply
from apps.translation.errors import TranslationProviderError
from apps.translation.models import Phrase
from apps.translation.services import translate_batch


class Command(BaseCommand):
    help = "현장 표현집과 채팅 빠른 답장의 번역 캐시를 미리 채운다."

    def add_arguments(self, parser):
        choices = [language for language in settings.SUPPORTED_LANGUAGES if language != "ko"]
        parser.add_argument("--target", action="append", choices=choices, help="번역 대상 언어. 여러 번 지정할 수 있다.")

    def handle(self, *args, **options):
        if settings.TRANSLATION_CACHE_TTL_DAYS <= 0:
            raise CommandError("사전 번역을 저장하려면 TRANSLATION_CACHE_TTL_DAYS를 1일 이상으로 설정해주세요.")
        targets = options["target"] or [language for language in settings.SUPPORTED_LANGUAGES if language != "ko"]
        texts = list(dict.fromkeys(chain(
            Phrase.objects.values_list("text_ko", flat=True),
            QuickReply.objects.values_list("text_ko", flat=True),
        )))
        batch_size = 24
        for target in dict.fromkeys(targets):
            try:
                for start in range(0, len(texts), batch_size):
                    translate_batch(texts[start : start + batch_size], "ko", target)
            except TranslationProviderError as error:
                raise CommandError(f"{target} 사전 번역 실패 ({error.get_codes()})") from error
            self.stdout.write(f"{target}: 표현 {len(texts)}건 준비")
