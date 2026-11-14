import django_filters as df
from django.db.models import Q

from .models import JobPost


class CharInFilter(df.BaseInFilter, df.CharFilter):
    pass


class JobFilter(df.FilterSet):
    """공고 목록/지도/주변검색 공통 필터"""

    q = df.CharFilter(method="filter_q", help_text="제목·회사명·설명·주소·직무 검색")
    region = CharInFilter(field_name="region__code", lookup_expr="in", help_text="시군구 코드 (콤마 구분)")
    category = CharInFilter(field_name="category__code", lookup_expr="in", help_text="업종 코드 (콤마 구분)")
    pay_type = df.ChoiceFilter(choices=JobPost.PayType.choices)
    min_pay = df.NumberFilter(field_name="pay_amount", lookup_expr="gte")
    max_pay = df.NumberFilter(field_name="pay_amount", lookup_expr="lte")
    period = df.ChoiceFilter(
        method="filter_period",
        choices=[("one_day", "하루"), ("short", "1주 이내"), ("mid", "1개월 이내"), ("long", "1개월 이상")],
        help_text="일하는 기간",
    )
    weekday = df.NumberFilter(method="filter_weekday", help_text="근무 요일 (0=월 … 6=일)")
    work_date = df.DateFilter(method="filter_work_date", help_text="해당 날짜에 근무하는 공고 (YYYY-MM-DD)")
    bbox = df.CharFilter(method="filter_bbox", help_text="지도 영역 'swLat,swLng,neLat,neLng' (목록보기 전환용)")
    urgent = df.BooleanFilter(field_name="is_urgent")
    beginner_ok = df.BooleanFilter()
    with_friend = df.BooleanFilter()
    lunch_provided = df.BooleanFilter()
    local_preferred = df.BooleanFilter()
    night_shift = df.BooleanFilter()

    class Meta:
        model = JobPost
        fields: list = []

    def filter_q(self, qs, name, value):
        return qs.filter(
            Q(title__icontains=value)
            | Q(company__name__icontains=value)
            | Q(description__icontains=value)
            | Q(address__icontains=value)
            | Q(work_type__icontains=value)
            | Q(region__name__icontains=value)
        )

    def filter_bbox(self, qs, name, value):
        try:
            sw_lat, sw_lng, ne_lat, ne_lng = (float(x) for x in value.split(","))
        except ValueError:
            return qs.none()
        return qs.filter(lat__gte=sw_lat, lat__lte=ne_lat, lng__gte=sw_lng, lng__lte=ne_lng)

    def filter_period(self, qs, name, value):
        return {
            "one_day": qs.filter(duration_days=1),
            "short": qs.filter(duration_days__lte=7),
            "mid": qs.filter(duration_days__lte=30),
            "long": qs.filter(duration_days__gt=30),
        }[value]

    def filter_weekday(self, qs, name, value):
        # weekdays 가 비어 있으면 매일 근무
        return qs.filter(Q(weekdays="") | Q(weekdays__contains=str(int(value))))

    def filter_work_date(self, qs, name, value):
        return qs.filter(start_date__lte=value).filter(Q(end_date__gte=value) | Q(end_date__isnull=True, start_date=value))
