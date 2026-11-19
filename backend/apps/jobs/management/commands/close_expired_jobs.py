from django.core.management.base import BaseCommand

from apps.jobs.services import close_expired_jobs


class Command(BaseCommand):
    help = "마감일/근무일이 지난 공고를 자동으로 마감 처리합니다. (cron 으로 매일 실행)"

    def handle(self, *args, **options):
        n = close_expired_jobs()
        self.stdout.write(self.style.SUCCESS(f"{n}건 마감 처리"))
