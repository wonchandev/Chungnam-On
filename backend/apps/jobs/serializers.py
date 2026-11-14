import re
from datetime import date

from django.utils import timezone

from django.db.models import Count, Q
from rest_framework import serializers

from apps.core.i18n import get_request_language
from apps.core.models import Region

from .models import Application, JobCategory, JobPost, Review

TAG_FIELDS = ("beginner_ok", "with_friend", "lunch_provided", "local_preferred", "night_shift")


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ("code", "name", "name_en")


class RegionBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("code", "name", "name_en")


def _translation(job, lang):
    if lang == "ko":
        return None
    for t in job.translations.all():  # prefetch 된 경우 추가 쿼리 없음
        if t.lang == lang:
            return t
    return None


class JobListSerializer(serializers.ModelSerializer):
    """목록/지도/관심 공고 카드. title 은 요청 언어(Accept-Language)로 번역된 값."""

    title = serializers.SerializerMethodField()
    work_type = serializers.SerializerMethodField()
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_is_agency = serializers.BooleanField(source="company.is_agency", read_only=True)
    company_temperature = serializers.FloatField(source="company.owner.temperature", read_only=True)
    category = CategorySerializer(read_only=True)
    region = RegionBriefSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    approved_count = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = JobPost
        fields = (
            "id", "title", "work_type", "image", "company_id", "company_name", "company_is_agency",
            "company_temperature", "category", "region", "address", "lat", "lng",
            "pay_type", "pay_amount", "start_date", "end_date", "duration_days",
            "start_time", "end_time", "headcount", "approved_count", "deadline", "status",
            "is_urgent", "tags", "is_bookmarked", "distance_km", "created_at",
        )

    def _lang(self):
        if "lang" not in self.context:
            self.context["lang"] = get_request_language(self.context["request"])
        return self.context["lang"]

    def get_title(self, obj) -> str:
        t = _translation(obj, self._lang())
        return t.title if t else obj.title

    def get_work_type(self, obj) -> str:
        t = _translation(obj, self._lang())
        return (t.work_type if t and t.work_type else obj.work_type)

    def get_tags(self, obj) -> dict:
        return {f: getattr(obj, f) for f in TAG_FIELDS}

    def get_approved_count(self, obj) -> int:
        if hasattr(obj, "approved_count_ann"):
            return obj.approved_count_ann
        return obj.applications.filter(status=Application.Status.APPROVED).count()

    def get_is_bookmarked(self, obj) -> bool:
        return obj.id in self.context.get("bookmarked_ids", ())

    def get_distance_km(self, obj) -> float | None:
        d = getattr(obj, "distance_km", None)
        return None if d is None else round(d, 2)


class JobDetailSerializer(JobListSerializer):
    description = serializers.SerializerMethodField()
    my_application_status = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + (
            "description", "weekdays", "break_minutes", "company", "my_application_status", "is_owner",
        )

    def get_description(self, obj) -> str:
        t = _translation(obj, self._lang())
        return t.description if t and t.description else obj.description

    def get_company(self, obj) -> dict:
        c = obj.company
        return {"id": c.id, "name": c.name, "is_agency": c.is_agency, "is_verified": c.is_verified,
                "temperature": c.owner.temperature, "review_count": c.owner.review_count}

    def get_my_application_status(self, obj) -> str | None:
        u = self.context["request"].user
        if not u.is_authenticated:
            return None
        return obj.applications.filter(applicant=u).values_list("status", flat=True).first()

    def get_is_owner(self, obj) -> bool:
        u = self.context["request"].user
        return u.is_authenticated and obj.company.owner_id == u.id


class JobWriteSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="code", queryset=JobCategory.objects.all())
    region = serializers.SlugRelatedField(
        slug_field="code", queryset=Region.objects.filter(level="sigungu"), help_text="시군구 코드 (예: 44130)"
    )

    class Meta:
        model = JobPost
        fields = (
            "id", "title", "description", "work_type", "image", "category", "pay_type", "pay_amount",
            "region", "address", "lat", "lng", "start_date", "end_date", "weekdays",
            "start_time", "end_time", "break_minutes", "headcount", "deadline", "is_urgent",
        ) + TAG_FIELDS
        read_only_fields = ("id",)

    def validate_pay_amount(self, v):
        if v <= 0:
            raise serializers.ValidationError("금액은 0보다 커야 합니다.")
        return v

    def validate_weekdays(self, v):
        if v and not re.fullmatch(r"[0-6](,[0-6])*", v):
            raise serializers.ValidationError("0~6 을 콤마로 구분해 입력하세요. 예: 0,1,2")
        return v

    def validate(self, attrs):
        g = lambda k: attrs.get(k, getattr(self.instance, k, None))
        start, end = g("start_date"), g("end_date")
        if end and start and end < start:
            raise serializers.ValidationError({"end_date": "종료일은 시작일 이후여야 합니다."})
        if self.instance is None and g("deadline") and g("deadline") < timezone.localdate():
            raise serializers.ValidationError({"deadline": "마감일은 오늘 이후여야 합니다."})
        lat, lng = g("lat"), g("lng")
        if (lat is None) != (lng is None):
            raise serializers.ValidationError({"lat": "lat 과 lng 는 함께 입력해야 합니다."})
        if lat is not None and not (33 <= lat <= 39 and 124 <= lng <= 132):
            raise serializers.ValidationError({"lat": "대한민국 범위의 좌표가 아닙니다."})
        if self.instance and attrs.get("headcount") is not None:
            approved = self.instance.applications.filter(status=Application.Status.APPROVED).count()
            if attrs["headcount"] < approved:
                raise serializers.ValidationError({"headcount": f"이미 승인된 인원({approved}명)보다 적을 수 없습니다."})
        return attrs


class ApplicantBriefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source="display_name")
    nationality = serializers.CharField()
    preferred_language = serializers.CharField()
    visa_type = serializers.CharField()
    temperature = serializers.FloatField()
    review_count = serializers.IntegerField()
    profile_image = serializers.ImageField()


class ApplicationSerializer(serializers.ModelSerializer):
    """내 구직활동 (근로자 시점)"""

    job = JobListSerializer(read_only=True)

    class Meta:
        model = Application
        fields = ("id", "status", "message", "job", "checked_in_at", "completed_at", "created_at", "updated_at")


class ApplyRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class JobApplicantSerializer(serializers.ModelSerializer):
    """지원자 목록 (사업주 시점). 연락처는 승인 후에만 노출."""

    applicant = ApplicantBriefSerializer(read_only=True)
    phone = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = ("id", "status", "message", "applicant", "phone", "checked_in_at", "completed_at", "created_at")

    def get_phone(self, obj) -> str | None:
        return obj.applicant.phone if obj.status == Application.Status.APPROVED else None


class ApplicationDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[Application.Status.APPROVED, Application.Status.REJECTED, Application.Status.PENDING])


class ReviewCreateSerializer(serializers.Serializer):
    reviewee = serializers.IntegerField(required=False, help_text="사업주가 평가할 때: 승인된 지원자의 user id")
    score = serializers.IntegerField(min_value=1, max_value=5)
    tags = serializers.ListField(child=serializers.ChoiceField(choices=Review.TAG_CHOICES), required=False, default=list)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.display_name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "job", "reviewer", "reviewer_name", "reviewee", "score", "tags", "comment", "created_at")


def annotate_jobs(qs):
    """목록 쿼리 최적화: 연관 조회 + 승인 인원 집계 + 번역 prefetch"""
    return (
        qs.select_related("company__owner", "category", "region")
        .prefetch_related("translations")
        .annotate(approved_count_ann=Count("applications", filter=Q(applications__status=Application.Status.APPROVED)))
        .order_by("-created_at", "-id")  # 집계(GROUP BY) 쿼리는 Meta.ordering 이 무시되므로 명시
    )


class JobDuplicateSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, help_text="새 공고의 시작일 (기본: 내일). 근무 기간 길이는 유지")


class RecommendedJobSerializer(JobListSerializer):
    match_score = serializers.SerializerMethodField()
    match_reasons = serializers.SerializerMethodField()

    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + ("match_score", "match_reasons")

    def get_match_score(self, obj) -> int:
        return getattr(obj, "match_score", 0)

    def get_match_reasons(self, obj) -> list:
        return getattr(obj, "match_reasons", [])


class AgencySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    address = serializers.CharField()
    description = serializers.CharField()
    is_verified = serializers.BooleanField()
    temperature = serializers.FloatField(source="owner.temperature")
    review_count = serializers.IntegerField(source="owner.review_count")
    open_job_count = serializers.SerializerMethodField()
    owner_id = serializers.IntegerField()

    def get_open_job_count(self, obj) -> int:
        return getattr(obj, "open_jobs", None) if hasattr(obj, "open_jobs") else obj.jobs.open().count()
