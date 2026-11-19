"""개발·시연용 데모 데이터 (사업주 3, 공고 12, 근로자 1). 여러 번 실행해도 중복 생성되지 않는다."""
import random
from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Company, User
from apps.core.models import Region
from apps.jobs.models import JobCategory, JobPost

BOSSES = [("boss1", "충남건설", "1111111111", False), ("boss2", "아산물류센터", "2222222222", False), ("boss3", "천안인력사무소", "3333333333", True)]
JOBS = [
    ("공장 신축 현장 보조", "construction", 300000, "44130", 36.8151, 127.1139, True),
    ("물류센터 상하차", "logistics", 120000, "44200", 36.7898, 127.0018, False),
    ("딸기 농장 수확", "agriculture", 110000, "44270", 36.8900, 126.6280, False),
    ("식품공장 포장", "manufacturing", 110000, "44130", 36.8300, 127.1500, False),
    ("마트 진열·정리", "retail", 100000, "44200", 36.7800, 127.0100, False),
    ("건물 철거 보조", "construction", 250000, "44130", 36.8000, 127.1200, True),
    ("야간 택배 분류", "logistics", 140000, "44270", 36.8950, 126.6300, False),
    ("조립 라인 단순작업", "manufacturing", 105000, "44200", 36.7950, 127.0300, False),
    ("주방 보조", "food", 98000, "44130", 36.8200, 127.1300, False),
    ("안전 관리 보조", "safety", 130000, "44270", 36.8850, 126.6200, False),
    ("하우스 농작업", "agriculture", 115000, "44200", 36.7700, 126.9900, False),
    ("자재 운반", "construction", 200000, "44130", 36.8100, 127.1000, True),
]


class Command(BaseCommand):
    def handle(self, *args, **opts):
        today = timezone.localdate()
        companies = []
        for u, name, num, agency in BOSSES:
            user, _ = User.objects.get_or_create(username=u, defaults={"role": "employer"})
            user.set_password("demo1234!"); user.save()
            c, _ = Company.objects.get_or_create(owner=user, defaults=dict(name=name, business_number=num, representative="홍길동", address="충남", is_agency=agency, is_verified=True))
            companies.append(c)
        w, _ = User.objects.get_or_create(username="worker1", defaults={"role": "worker", "preferred_language": "vi", "nationality": "베트남", "visa_type": "E-9", "region": Region.objects.filter(code="44130").first()})
        w.set_password("demo1234!"); w.save()
        n = 0
        for i, (title, cat, pay, region, lat, lng, urgent) in enumerate(JOBS):
            if JobPost.objects.filter(title=title).exists():
                continue
            JobPost.objects.create(
                company=companies[i % 3], category=JobCategory.objects.get(code=cat), title=title,
                description=f"{title} 일자리입니다. 성실하게 일하실 분을 모집합니다.", work_type="현장 보조",
                pay_type="daily", pay_amount=pay, region=Region.objects.get(code=region), address="충남",
                lat=lat + random.uniform(-0.01, 0.01), lng=lng + random.uniform(-0.01, 0.01),
                start_date=today + timedelta(days=1 + i % 5), start_time=time(8, 0), end_time=time(17, 0),
                headcount=3, is_urgent=urgent, beginner_ok=i % 2 == 0, lunch_provided=i % 3 == 0,
            )
            n += 1
        self.stdout.write(f"공고 {n}건 생성. 로그인: worker1 / boss1~3, 비밀번호 demo1234!")
