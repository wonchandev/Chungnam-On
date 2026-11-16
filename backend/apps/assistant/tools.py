"""챗봇이 호출하는 기능 연동 도구 (OpenAI function calling).
쓰기 작업(지원·관심 등록)은 confirmed=true 일 때만 실행하고, 아니면 사용자 확인을 먼저 요청하게 한다."""
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.jobs.models import Application, JobPost

TOOLS = [
    {"type": "function", "function": {
        "name": "search_jobs", "description": "모집중인 일자리 공고를 검색한다. 일당 높은 순/최신순 정렬 가능.",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string", "description": "제목·직무 검색어(한국어)"},
            "region": {"type": "string", "description": "지역명 일부(예: 천안, 아산)"},
            "near_me": {"type": "boolean", "description": "내 거주 지역 주변만"},
            "category": {"type": "string", "description": "manufacturing, construction, agriculture, logistics, retail, safety, food, etc"},
            "min_pay": {"type": "integer", "description": "최소 급여(원)"},
            "sort": {"type": "string", "enum": ["pay", "latest"]},
        }}}},
    {"type": "function", "function": {
        "name": "my_applications", "description": "내 지원 현황(대기/승인/거절)과 근무 일정을 조회한다.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "apply_job", "description": "공고에 지원한다. 사용자가 명시적으로 동의한 뒤에만 confirmed=true 로 호출한다.",
        "parameters": {"type": "object", "properties": {
            "job_id": {"type": "integer"}, "confirmed": {"type": "boolean"}}, "required": ["job_id"]}}},
    {"type": "function", "function": {
        "name": "bookmark_job", "description": "공고를 관심 공고로 저장한다. 사용자가 동의한 뒤에만 confirmed=true 로 호출한다.",
        "parameters": {"type": "object", "properties": {
            "job_id": {"type": "integer"}, "confirmed": {"type": "boolean"}}, "required": ["job_id"]}}},
    {"type": "function", "function": {
        "name": "estimate_pay", "description": "근무 급여를 단순 계산한다(세금·공제·수당 제외).",
        "parameters": {"type": "object", "properties": {
            "pay_type": {"type": "string", "enum": ["daily", "hourly"]},
            "amount": {"type": "integer", "description": "일급 또는 시급(원)"},
            "days": {"type": "integer"}, "hours_per_day": {"type": "number"}},
            "required": ["pay_type", "amount", "days"]}}},
]


def _job_dict(j: JobPost) -> dict:
    return {"id": j.id, "title": j.title, "company": j.company.name, "region": j.region.name,
            "pay_type": j.pay_type, "pay_amount": j.pay_amount, "start_date": str(j.start_date),
            "start_time": str(j.start_time)[:5], "end_time": str(j.end_time)[:5]}


def search_jobs(user, keyword="", region="", near_me=False, category="", min_pay=0, sort="latest", **_):
    qs = JobPost.objects.open().select_related("company", "region")
    if keyword:
        qs = qs.filter(title__icontains=keyword) | qs.filter(work_type__icontains=keyword)
    if region:
        qs = qs.filter(region__name__icontains=region)
    if near_me and user.region_id:
        qs = qs.filter(region_id__in=[user.region_id, user.region.parent_id])
    if category:
        qs = qs.filter(category__code=category)
    if min_pay:
        qs = qs.filter(pay_amount__gte=min_pay)
    qs = qs.order_by("-pay_amount" if sort == "pay" else "-created_at")[:5]
    return {"jobs": [_job_dict(j) for j in qs]}


def my_applications(user, **_):
    apps = Application.objects.filter(applicant=user).select_related("job__company", "job__region")[:10]
    return {"applications": [{"status": a.status, **_job_dict(a.job)} for a in apps]}


def _call_view(view_cls, user, job_id: int):
    """기존 API 뷰를 그대로 호출해 검증 규칙(마감·정원·중복·권한)을 재사용한다."""
    req = APIRequestFactory().post(f"/api/jobs/{job_id}/", {}, format="json")
    force_authenticate(req, user=user)
    res = view_cls.as_view()(req, pk=job_id)
    if res.status_code < 300:
        return {"ok": True}
    return {"ok": False, "error": res.data.get("message") if isinstance(res.data, dict) else "failed"}


def _confirm_gate(user, job_id, confirmed, action):
    job = JobPost.objects.filter(pk=job_id).first()
    if not job:
        return {"ok": False, "error": "공고를 찾을 수 없습니다."}
    if not confirmed:
        return {"needs_confirmation": True, "action": action, "job": _job_dict(job),
                "instruction": "Ask the user to confirm clearly, then call again with confirmed=true."}
    return None


def apply_job(user, job_id, confirmed=False, **_):
    from apps.jobs.views import ApplyView

    return _confirm_gate(user, job_id, confirmed, "apply") or _call_view(ApplyView, user, job_id)


def bookmark_job(user, job_id, confirmed=False, **_):
    from apps.jobs.views import BookmarkView

    return _confirm_gate(user, job_id, confirmed, "bookmark") or _call_view(BookmarkView, user, job_id)


def estimate_pay(user, pay_type, amount, days, hours_per_day=8, **_):
    per_day = amount if pay_type == "daily" else amount * hours_per_day
    return {"total_krw": int(per_day * days), "per_day_krw": int(per_day),
            "note": "세금·4대보험 공제, 연장·야간·휴일 수당은 포함되지 않은 단순 계산입니다."}


_FUNCS = {f.__name__: f for f in (search_jobs, my_applications, apply_job, bookmark_job, estimate_pay)}


def run_tool(user, name: str, args: dict) -> dict:
    fn = _FUNCS.get(name)
    if not fn:
        return {"error": f"unknown tool {name}"}
    try:
        return fn(user, **args)
    except Exception as e:  # 모델이 잘못된 인자를 줄 수 있음 → 에러를 모델에 돌려준다
        return {"error": str(e)}
