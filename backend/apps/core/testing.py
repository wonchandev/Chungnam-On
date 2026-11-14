"""테스트 공용 헬퍼"""
from datetime import date, time, timedelta

from rest_framework.test import APIClient

from apps.accounts.models import Company, User
from apps.core.models import Region
from apps.jobs.models import JobCategory, JobPost

PW = "Str0ng-pass!23"


def make_worker(username="worker1", lang="ko", **kw):
    return User.objects.create_user(username=username, password=PW, role="worker", preferred_language=lang, **kw)


def make_employer(username="boss1", name="충남 건설", number="1234567890", **kw):
    u = User.objects.create_user(username=username, password=PW, role="employer", **kw)
    Company.objects.create(owner=u, name=name, business_number=number, representative="홍길동", address="천안시")
    return u


def client_for(user=None):
    c = APIClient()
    if user:
        c.force_authenticate(user)
    return c


def make_job(company, **kw):
    defaults = dict(
        company=company,
        category=JobCategory.objects.get(code="construction"),
        title="공장 신축 현장 보조",
        pay_type="daily",
        pay_amount=300000,
        region=Region.objects.get(code="44130"),
        lat=36.8151, lng=127.1139,
        start_date=date.today() + timedelta(days=1),
        start_time=time(8, 0), end_time=time(17, 0),
        headcount=2,
    )
    defaults.update(kw)
    return JobPost.objects.create(**defaults)
