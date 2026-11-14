from collections import defaultdict

from django.db.models import Q
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import JobFilter
from .models import JobPost
from .serializers import JobListSerializer, annotate_jobs
from .services import haversine_km
from .views import JobContextMixin


class BoundsSerializer(serializers.Serializer):
    sw_lat = serializers.FloatField(min_value=-90, max_value=90, required=False, help_text="남서쪽 위도")
    sw_lng = serializers.FloatField(min_value=-180, max_value=180, required=False, help_text="남서쪽 경도")
    ne_lat = serializers.FloatField(min_value=-90, max_value=90, required=False, help_text="북동쪽 위도")
    ne_lng = serializers.FloatField(min_value=-180, max_value=180, required=False, help_text="북동쪽 경도")

    def validate(self, a):
        keys = ("sw_lat", "sw_lng", "ne_lat", "ne_lng")
        given = [k in a for k in keys]
        if any(given) and not all(given):
            raise serializers.ValidationError("sw_lat, sw_lng, ne_lat, ne_lng 는 모두 함께 보내야 합니다.")
        if all(given) and (a["sw_lat"] > a["ne_lat"] or a["sw_lng"] > a["ne_lng"]):
            raise serializers.ValidationError("남서쪽 좌표가 북동쪽보다 클 수 없습니다.")
        return a


class ClusterQuerySerializer(BoundsSerializer):
    zoom = serializers.IntegerField(min_value=1, max_value=20, default=10, help_text="지도 줌 레벨")


class NearbyQuerySerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)
    radius = serializers.FloatField(min_value=0.1, max_value=50, default=5, help_text="반경(km)")
    limit = serializers.IntegerField(min_value=1, max_value=200, default=50)


class MarkerSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source="category.code")

    class Meta:
        model = JobPost
        fields = ("id", "title", "lat", "lng", "pay_type", "pay_amount", "category", "is_urgent")


def map_queryset(request, bounds=None):
    """지도 공통: 모집중 + 좌표 있음 + 목록과 동일한 필터 + (선택) bbox"""
    qs = JobPost.objects.open().filter(lat__isnull=False, lng__isnull=False)
    qs = JobFilter(request.query_params, queryset=qs, request=request).qs
    if bounds and "sw_lat" in bounds:
        qs = qs.filter(
            lat__gte=bounds["sw_lat"], lat__lte=bounds["ne_lat"],
            lng__gte=bounds["sw_lng"], lng__lte=bounds["ne_lng"],
        )
    return qs


class MapMarkerView(APIView):
    """지도 마커: bbox 안의 공고 (최대 500건). 필터는 공고 목록과 동일 (`category`, `urgent`, `beginner_ok` …)"""

    permission_classes = [permissions.AllowAny]
    LIMIT = 500

    @extend_schema(parameters=[BoundsSerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        b = BoundsSerializer(data=request.query_params)
        b.is_valid(raise_exception=True)
        qs = map_queryset(request, b.validated_data).select_related("category").order_by("-is_urgent", "-created_at")
        total = qs.count()
        return Response({"total": total, "truncated": total > self.LIMIT,
                         "results": MarkerSerializer(qs[: self.LIMIT], many=True).data})


class MapClusterView(APIView):
    """줌 레벨별 격자 클러스터: 각 클러스터의 중심 좌표와 공고 건수 (예: 250 / 98 / 10)"""

    permission_classes = [permissions.AllowAny]

    @extend_schema(parameters=[ClusterQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        q = ClusterQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        d = q.validated_data
        qs = map_queryset(request, d)
        cell = 180 / (2 ** d["zoom"])  # 줌 10 ≈ 0.18° (약 20km), 줌 13 ≈ 0.02°
        grid = defaultdict(lambda: [0, 0.0, 0.0, []])
        for job_id, lat, lng in qs.values_list("id", "lat", "lng"):
            g = grid[(int(lat // cell), int(lng // cell))]
            g[0] += 1; g[1] += lat; g[2] += lng
            if len(g[3]) < 3:
                g[3].append(job_id)
        clusters = [
            {"lat": round(s_lat / n, 6), "lng": round(s_lng / n, 6), "count": n, "sample_job_ids": ids}
            for n, s_lat, s_lng, ids in grid.values()
        ]
        clusters.sort(key=lambda c: -c["count"])
        return Response({"zoom": d["zoom"], "total": sum(c["count"] for c in clusters), "clusters": clusters})


class NearbyJobView(JobContextMixin, APIView):
    """현재 위치 기반 주변 공고 (가까운 순, 거리 km 포함). 필터는 공고 목록과 동일."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(parameters=[NearbyQuerySerializer], responses=OpenApiTypes.OBJECT)
    def get(self, request):
        q = NearbyQuerySerializer(data=request.query_params)
        q.is_valid(raise_exception=True)
        d = q.validated_data
        lat, lng, radius = d["lat"], d["lng"], d["radius"]
        dlat = radius / 111.0
        dlng = radius / (111.0 * max(0.01, abs(__import__("math").cos(__import__("math").radians(lat)))))
        base = map_queryset(request).filter(lat__gte=lat - dlat, lat__lte=lat + dlat, lng__gte=lng - dlng, lng__lte=lng + dlng)
        jobs = []
        for job in annotate_jobs(base):
            dist = haversine_km(lat, lng, job.lat, job.lng)
            if dist <= radius:
                job.distance_km = dist
                jobs.append(job)
        jobs.sort(key=lambda j: j.distance_km)
        jobs = jobs[: d["limit"]]
        ser = JobListSerializer(jobs, many=True, context=self.get_serializer_context())
        return Response({"count": len(jobs), "results": ser.data})

    def get_serializer_context(self):
        from apps.jobs.models import Bookmark

        u = self.request.user
        return {
            "request": self.request,
            "bookmarked_ids": set(Bookmark.objects.filter(user=u).values_list("job_id", flat=True)) if u.is_authenticated else set(),
        }
