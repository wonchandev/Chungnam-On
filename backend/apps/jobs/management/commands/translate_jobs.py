import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.jobs.translation_tasks import requeue_failed_translations, translate_next_job


class Command(BaseCommand):
    help = "공고 번역 대기열을 처리하는 워커를 실행합니다."
    requires_migrations_checks = True

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="현재 처리 가능한 작업을 모두 처리한 뒤 종료")
        parser.add_argument("--retry-failed", action="store_true", help="실패한 공고 번역 작업을 다시 대기열에 등록")

    def handle(self, *args, **options):
        if options["retry_failed"]:
            count = requeue_failed_translations()
            self.stdout.write(f"공고 번역 작업 {count}건 재등록")
        self.stdout.write("공고 번역 워커 시작")
        try:
            while True:
                close_old_connections()
                if translate_next_job():
                    continue
                if options["once"]:
                    return
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("공고 번역 워커 종료")
