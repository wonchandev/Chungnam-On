from django.core.management.base import BaseCommand

from apps.assistant.models import AdminGuide
from apps.assistant.rag import index_guide


class Command(BaseCommand):
    help = "행정 가이드를 문단 단위로 나눠 임베딩 색인 (OPENAI_API_KEY 필요)"

    def handle(self, *args, **opts):
        total = 0
        for g in AdminGuide.objects.filter(is_published=True):
            total += index_guide(g)
        self.stdout.write(f"indexed {total} chunks")
