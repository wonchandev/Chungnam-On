from datetime import date, timedelta

from django.utils import timezone

from django.db import transaction
from django.db.models import Count, F, Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.exceptions import ServiceError
from apps.core.services import is_blocked_between, notify

from .filters import JobFilter
from .models import Application, Bookmark, JobCategory, JobPost, RecentView, Review, SearchLog
from .permissions import IsEmployer, IsWorker
from .serializers import (
    ApplicationDecisionSerializer, ApplicationSerializer, ApplyRequestSerializer, CategorySerializer,
    AgencySerializer, JobApplicantSerializer, JobDetailSerializer, JobDuplicateSerializer, JobListSerializer,
    JobWriteSerializer, RecommendedJobSerializer,
    ReviewCreateSerializer, ReviewSerializer, annotate_jobs,
)
from .services import apply_review_score, recommend_jobs, sync_job_translations

PARSERS = [JSONParser, MultiPartParser, FormParser]


class JobContextMixin:
    """직렬화 시 현재 유저의 관심 공고 id 를 1회 쿼리로 미리 조회"""

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        u = self.request.user
        ctx["bookmarked_ids"] = (
            set(Bookmark.objects.filter(user=u).values_list("job_id", flat=True)) if u.is_authenticated else set()
        )
        return ctx


def get_owned_job(request, pk):
    from django.shortcuts import get_object_or_404

    return get_object_or_404(JobPost.objects.select_related("company"), pk=pk, company__owner=request.user)


# ───────────────────────── 공고 CRUD / 조회 ─────────────────────────
class JobListCreateView(JobContextMixin, generics.ListCreateAPIView):
    """GET: 공고 목록 (모집중만, 필터/정렬/검색) · POST: 공고 등록 (사업주)"""

    filterset_class = JobFilter
    ordering_fields = ["created_at", "pay_amount", "deadline", "start_date"]
    parser_classes = PARSERS

    def get_permissions(self):
        return [IsEmployer()] if self.request.method == "POST" else [permissions.AllowAny()]

    def get_serializer_class(self):
        return JobWriteSerializer if self.request.method == "POST" else JobListSerializer

    def get_queryset(self):
        return annotate_jobs(JobPost.objects.open())

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        q = self.request.query_params.get("q", "").strip().lower()
        if len(q) >= 2 and not self.request.query_params.get("page"):  # 첫 페이지 검색만 집계
            SearchLog.objects.create(q=q[:100])
        if self.request.query_params.get("ordering", "").lstrip("-") == "deadline":  # 마감 없는 공고는 뒤로
            desc = self.request.query_params["ordering"].startswith("-")
            qs = qs.order_by(F("deadline").desc(nulls_last=True) if desc else F("deadline").asc(nulls_last=True), "-created_at")
        return qs

    def create(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        job = ser.save(company=request.user.company)
        sync_job_translations(job)
        out = JobDetailSerializer(annotate_jobs(JobPost.objects.filter(pk=job.pk)).get(), context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)


class JobDetailView(JobContextMixin, generics.RetrieveUpdateDestroyAPIView):
    """GET: 공고 상세 · PATCH: 수정 (본인) · DELETE: 삭제=취소 처리 (본인)"""

    parser_classes = PARSERS

    def get_permissions(self):
        return [permissions.AllowAny()] if self.request.method == "GET" else [IsEmployer()]

    def get_queryset(self):
        qs = annotate_jobs(JobPost.objects.exclude(status=JobPost.Status.CANCELLED).filter(is_hidden=False))
        if self.request.method != "GET":
            qs = qs.filter(company__owner=self.request.user)
        return qs

    def get_serializer_class(self):
        return JobDetailSerializer if self.request.method == "GET" else JobWriteSerializer

    def retrieve(self, request, *args, **kwargs):
        resp = super().retrieve(request, *args, **kwargs)
        if request.user.is_authenticated:
            RecentView.objects.update_or_create(user=request.user, job_id=kwargs["pk"])
        return resp

    def update(self, request, *args, **kwargs):
        job = self.get_object()
        ser = JobWriteSerializer(job, data=request.data, partial=True, context=self.get_serializer_context())
        ser.is_valid(raise_exception=True)
        job = ser.save()
        sync_job_translations(job)
        out = JobDetailSerializer(self.get_queryset().get(pk=job.pk), context=self.get_serializer_context())
        return Response(out.data)

    def perform_destroy(self, instance):
        instance.status = JobPost.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])


class JobCloseView(APIView):
    """모집 마감 처리 (본인 공고)"""

    permission_classes = [IsEmployer]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        job = get_owned_job(request, pk)
        job.status = JobPost.Status.CLOSED
        job.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyJobListView(JobContextMixin, generics.ListAPIView):
    """내 공고 목록 (사업주). `?status=open|closed|cancelled`"""

    serializer_class = JobListSerializer
    permission_classes = [IsEmployer]
    filterset_class = JobFilter
    ordering_fields = ["created_at", "pay_amount", "deadline", "start_date"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JobPost.objects.none()
        qs = annotate_jobs(JobPost.objects.filter(company__owner=self.request.user))
        st = self.request.query_params.get("status")
        return qs.filter(status=st) if st else qs


class UrgentJobListView(JobContextMixin, generics.ListAPIView):
    """긴급 채용·마감임박 공고 (홈 캐러셀). `?limit=10`"""

    serializer_class = JobListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends: list = []

    def get_queryset(self):
        limit = min(int(self.request.query_params.get("limit", 10) or 10), 50)
        soon = timezone.localdate() + timedelta(days=2)
        qs = annotate_jobs(JobPost.objects.open()).filter(Q(is_urgent=True) | Q(deadline__lte=soon))
        return qs.order_by(F("deadline").asc(nulls_last=True), "-created_at")[:limit]


class PopularCategoryView(APIView):
    """지금 많이 찾는 일자리: 모집중 공고가 많은 업종 순. `?limit=8`"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(parameters=[OpenApiParameter("limit", int)], responses=CategorySerializer(many=True))
    def get(self, request):
        limit = min(int(request.query_params.get("limit", 8) or 8), 20)
        today = timezone.localdate()
        open_q = Q(jobs__status="open") & (Q(jobs__deadline__isnull=True) | Q(jobs__deadline__gte=today))
        cats = (
            JobCategory.objects.annotate(open_count=Count("jobs", filter=open_q))
            .filter(open_count__gt=0).order_by("-open_count", "order")[:limit]
        )
        data = [{**CategorySerializer(c).data, "open_count": c.open_count} for c in cats]
        return Response(data)


class CategoryListView(generics.ListAPIView):
    """업종 목록"""

    queryset = JobCategory.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


# ───────────────────────── 지원 / 승인 ─────────────────────────
class ApplyView(APIView):
    """지원하기 (근로자). 마감·정원·중복 검증."""

    permission_classes = [IsWorker]

    @extend_schema(request=ApplyRequestSerializer, responses={201: ApplicationSerializer})
    @transaction.atomic
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404

        job = get_object_or_404(JobPost.objects.select_for_update(), pk=pk)
        body = ApplyRequestSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        if not job.is_open:
            raise ServiceError("job_closed", "마감된 공고입니다.", 409)
        if Application.objects.filter(job=job, applicant=request.user).exists():
            raise ServiceError("already_applied", "이미 지원한 공고입니다.", 409)
        if job.applications.filter(status=Application.Status.APPROVED).count() >= job.headcount:
            raise ServiceError("headcount_full", "모집 인원이 모두 찼습니다.", 409)
        app = Application.objects.create(job=job, applicant=request.user, message=body.validated_data["message"])
        from apps.chat.services import get_or_create_room

        owner = job.company.owner
        room = None
        if not is_blocked_between(request.user, owner):
            room = get_or_create_room(request.user, owner, job)  # 지원하면 문의 채팅방 자동 생성
        notify(owner, "application", "새 지원자가 있어요", f"{request.user.display_name} · {job.title}", job_id=job.id, application_id=app.id)
        data = dict(ApplicationSerializer(app, context={"request": request}).data)
        data["chat_room_id"] = room.id if room else None
        return Response(data, status=status.HTTP_201_CREATED)


class MyApplicationListView(JobContextMixin, generics.ListAPIView):
    """내 구직활동. `?status=pending|approved|rejected`"""

    serializer_class = ApplicationSerializer
    permission_classes = [IsWorker]
    filterset_fields = ["status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Application.objects.none()
        return Application.objects.filter(applicant=self.request.user).select_related(
            "job__company__owner", "job__category", "job__region"
        ).prefetch_related("job__translations")


class ApplicationDetailView(APIView):
    """DELETE: 지원 취소 (본인) · PATCH: 승인/거절 (해당 공고의 사업주)"""

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        deleted, _ = Application.objects.filter(pk=pk, applicant=request.user).delete()
        if not deleted:
            raise ServiceError("not_found", "지원 내역을 찾을 수 없습니다.", 404)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=ApplicationDecisionSerializer, responses=JobApplicantSerializer)
    @transaction.atomic
    def patch(self, request, pk):
        from django.shortcuts import get_object_or_404

        app = get_object_or_404(
            Application.objects.select_related("job", "applicant"), pk=pk, job__company__owner=request.user
        )
        ser = ApplicationDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        new = ser.validated_data["status"]
        if new == Application.Status.APPROVED and app.status != Application.Status.APPROVED:
            job = JobPost.objects.select_for_update().get(pk=app.job_id)
            if job.applications.filter(status=Application.Status.APPROVED).count() >= job.headcount:
                raise ServiceError("headcount_full", "모집 인원이 모두 찼습니다.", 409)
        changed = app.status != new
        app.status = new
        app.save(update_fields=["status", "updated_at"])
        if changed and new in (Application.Status.APPROVED, Application.Status.REJECTED):
            label = "승인" if new == Application.Status.APPROVED else "거절"
            notify(app.applicant, "decision", f"지원이 {label}되었어요", app.job.title, job_id=app.job_id, application_id=app.id)
        return Response(JobApplicantSerializer(app, context={"request": request}).data)


class JobApplicantListView(generics.ListAPIView):
    """지원자 목록 (사업주, 본인 공고). `?status=pending`"""

    serializer_class = JobApplicantSerializer
    permission_classes = [IsEmployer]
    filterset_fields = ["status"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Application.objects.none()
        job = get_owned_job(self.request, self.kwargs["pk"])
        return job.applications.select_related("applicant")


# ───────────────────────── 관심 공고 ─────────────────────────
class BookmarkView(APIView):
    """POST: 관심 공고 등록 · DELETE: 해제 (둘 다 멱등)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404

        job = get_object_or_404(JobPost, pk=pk)
        Bookmark.objects.get_or_create(user=request.user, job=job)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={204: None})
    def delete(self, request, pk):
        Bookmark.objects.filter(user=request.user, job_id=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookmarkListView(JobContextMixin, generics.ListAPIView):
    """관심 공고 목록"""

    serializer_class = JobListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        ids = Bookmark.objects.filter(user=self.request.user).order_by("-created_at").values_list("job_id", flat=True)
        order = {j: i for i, j in enumerate(ids)}
        jobs = list(annotate_jobs(JobPost.objects.filter(id__in=order)))
        return sorted(jobs, key=lambda j: order[j.id])


# ───────────────────────── 평판 ─────────────────────────
class JobReviewCreateView(APIView):
    """근무 후 평가: 지원자(승인됨) → 사업주, 사업주 → 승인된 지원자(`reviewee` 지정)"""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=ReviewCreateSerializer, responses={201: ReviewSerializer})
    @transaction.atomic
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404

        job = get_object_or_404(JobPost.objects.select_related("company"), pk=pk)
        ser = ReviewCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        owner = job.company.owner
        # 근무 완료 처리(complete)된 지원만 평가 가능
        approved = Application.objects.filter(job=job, status=Application.Status.APPROVED, completed_at__isnull=False)
        if request.user == owner:
            reviewee_id = d.get("reviewee")
            if not reviewee_id or not approved.filter(applicant_id=reviewee_id).exists():
                raise ServiceError("invalid_reviewee", "근무 완료 처리된 지원자만 평가할 수 있습니다. (reviewee 필요)", 400)
            reviewee = User.objects.get(pk=reviewee_id)
        elif approved.filter(applicant=request.user).exists():
            reviewee = owner
        else:
            raise ServiceError("forbidden", "근무 완료 처리된 근무자/사업주만 평가할 수 있습니다.", 403)

        if Review.objects.filter(job=job, reviewer=request.user, reviewee=reviewee).exists():
            raise ServiceError("already_reviewed", "이미 평가했습니다.", 409)
        review = Review.objects.create(
            job=job, reviewer=request.user, reviewee=reviewee, score=d["score"], tags=d["tags"], comment=d["comment"]
        )
        apply_review_score(reviewee, d["score"])
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ReputationView(APIView):
    """유저 평판: 온도, 후기 수, 태그 통계, 최근 후기"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404

        user = get_object_or_404(User, pk=pk)
        reviews = Review.objects.filter(reviewee=user)
        tag_counts: dict = {}
        for tags in reviews.values_list("tags", flat=True):
            for t in tags:
                tag_counts[t] = tag_counts.get(t, 0) + 1
        return Response({
            "user_id": user.id,
            "name": user.display_name,
            "temperature": user.temperature,
            "review_count": user.review_count,
            "tag_counts": tag_counts,
            "recent_reviews": ReviewSerializer(reviews.select_related("reviewer")[:10], many=True).data,
        })


# ───────────────────────── P1: 공고 복사 / 추천 / 티커 / 최근 / 인기 검색어 ─────────────────────────
class JobDuplicateView(APIView):
    """공고 복사(재등록): 내용과 근무 기간 길이를 유지한 새 공고를 만든다. 마감일은 비움, 지원자는 복사하지 않음."""

    permission_classes = [IsEmployer]

    @extend_schema(request=JobDuplicateSerializer, responses={201: JobDetailSerializer})
    def post(self, request, pk):
        src = get_owned_job(request, pk)
        body = JobDuplicateSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        start = body.validated_data.get("start_date") or (timezone.localdate() + timedelta(days=1))
        length = (src.end_date - src.start_date) if src.end_date else None
        fields = [f.name for f in JobPost._meta.concrete_fields if f.name not in
                  ("id", "created_at", "updated_at", "start_date", "end_date", "duration_days", "deadline", "status", "is_hidden")]
        new = JobPost(**{f: getattr(src, f) for f in fields}, start_date=start,
                      end_date=(start + length) if length is not None else None)
        new.save()
        sync_job_translations(new)
        out = JobDetailSerializer(annotate_jobs(JobPost.objects.filter(pk=new.pk)).get(), context={"request": request, "bookmarked_ids": set()})
        return Response(out.data, status=status.HTTP_201_CREATED)


class RecommendedJobView(JobContextMixin, generics.ListAPIView):
    """나에게 딱 맞는 일자리 / AI 추천 (규칙 기반: 희망 지역·가능 업종·요일·초보 가능·평판). 비로그인은 최신순. `?limit=20`"""

    serializer_class = RecommendedJobSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JobPost.objects.none()
        limit = min(int(self.request.query_params.get("limit", 20) or 20), 50)
        return recommend_jobs(self.request.user, limit)


class JobTickerView(APIView):
    """홈 상단 배너용 실시간 신규 공고: '[일급 250,000] 아산시 물류센터'"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        jobs = annotate_jobs(JobPost.objects.open()).order_by("-created_at")[:10]
        return Response([{
            "id": j.id,
            "label": f"[{j.get_pay_type_display()} {j.pay_amount:,}] {j.region.name} {j.category.name}",
            "pay_type": j.pay_type, "pay_amount": j.pay_amount,
            "region": j.region.name, "category": j.category.code,
        } for j in jobs])


class RecentJobListView(JobContextMixin, generics.ListAPIView):
    """최근 본 공고 (최대 20건)"""

    serializer_class = JobListSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return JobPost.objects.none()
        ids = list(RecentView.objects.filter(user=self.request.user).values_list("job_id", flat=True)[:20])
        order = {j: i for i, j in enumerate(ids)}
        jobs = annotate_jobs(JobPost.objects.filter(id__in=order, is_hidden=False))
        return sorted(jobs, key=lambda j: order[j.id])


class PopularSearchView(APIView):
    """인기 검색어 (최근 7일). `?limit=10`"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        limit = min(int(request.query_params.get("limit", 10) or 10), 30)
        since = timezone.now() - timedelta(days=7)
        rows = (SearchLog.objects.filter(created_at__gte=since).values("q").annotate(n=Count("id")).order_by("-n", "q")[:limit])
        return Response([{"keyword": r["q"], "count": r["n"]} for r in rows])


# ───────────────────────── P1: 출근 확인 / 근무 완료 ─────────────────────────
class _AttendanceBase(APIView):
    permission_classes = [IsEmployer]

    def get_app(self, request, pk):
        from django.shortcuts import get_object_or_404

        return get_object_or_404(
            Application.objects.select_related("job", "applicant"), pk=pk, job__company__owner=request.user
        )


class CheckInView(_AttendanceBase):
    """출근 확인 (사업주): 승인된 지원자, 근무 시작일 이후에만 가능. 멱등."""

    @extend_schema(request=None, responses=JobApplicantSerializer)
    def post(self, request, pk):
        app = self.get_app(request, pk)
        if app.status != Application.Status.APPROVED:
            raise ServiceError("not_approved", "승인된 지원자만 출근 확인할 수 있습니다.", 409)
        if app.job.start_date > timezone.localdate():
            raise ServiceError("not_started", "근무 시작일 이전에는 출근 확인을 할 수 없습니다.", 409)
        if not app.checked_in_at:
            app.checked_in_at = timezone.now()
            app.save(update_fields=["checked_in_at", "updated_at"])
        return Response(JobApplicantSerializer(app, context={"request": request}).data)


class CompleteView(_AttendanceBase):
    """근무 완료 처리 (사업주): 출근 확인된 지원자. 완료되면 양쪽 모두 후기를 작성할 수 있고 알림이 간다. 멱등."""

    @extend_schema(request=None, responses=JobApplicantSerializer)
    def post(self, request, pk):
        app = self.get_app(request, pk)
        if not app.checked_in_at:
            raise ServiceError("not_checked_in", "출근 확인 후에 완료 처리할 수 있습니다.", 409)
        if not app.completed_at:
            app.completed_at = timezone.now()
            app.save(update_fields=["completed_at", "updated_at"])
            notify(app.applicant, "completed", "근무가 완료되었어요. 후기를 남겨주세요", app.job.title, job_id=app.job_id)
        return Response(JobApplicantSerializer(app, context={"request": request}).data)


# ───────────────────────── P1: 인력사무소 ─────────────────────────
class AgencyListView(generics.ListAPIView):
    """인력사무소 목록 (`?q=` 상호/주소 검색, 온도 높은 순)"""

    serializer_class = AgencySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends: list = []

    def get_queryset(self):
        from django.utils import timezone as tz

        from apps.accounts.models import Company

        today = tz.localdate()
        qs = Company.objects.filter(is_agency=True, owner__is_active=True).select_related("owner").annotate(
            open_jobs=Count("jobs", filter=Q(jobs__status="open", jobs__is_hidden=False) & (Q(jobs__deadline__isnull=True) | Q(jobs__deadline__gte=today)))
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(address__icontains=q))
        return qs.order_by("-owner__temperature", "-open_jobs", "id")


class AgencyDetailView(APIView):
    """인력사무소 상세: 소개, 온도, 모집중 공고 목록"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404

        from apps.accounts.models import Company

        c = get_object_or_404(Company.objects.select_related("owner"), pk=pk, is_agency=True, owner__is_active=True)
        ctx = {"request": request, "bookmarked_ids": set(Bookmark.objects.filter(user=request.user).values_list("job_id", flat=True)) if request.user.is_authenticated else set()}
        jobs = annotate_jobs(c.jobs.open())[:30]
        return Response({**AgencySerializer(c).data, "jobs": JobListSerializer(jobs, many=True, context=ctx).data})
