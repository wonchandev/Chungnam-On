from django.contrib import admin

from .models import AdminGuide, AdminGuideTranslation, ChatTurn


class GuideTranslationInline(admin.StackedInline):
    model = AdminGuideTranslation
    extra = 0


@admin.register(AdminGuide)
class AdminGuideAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "view_count", "updated_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "body")
    inlines = [GuideTranslationInline]
    actions = ["reindex"]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._index(request, [form.instance])

    @admin.action(description="선택한 가이드 임베딩 재색인")
    def reindex(self, request, queryset):
        self._index(request, queryset)

    def _index(self, request, guides):
        from . import llm
        from .rag import index_guide

        if not llm.llm_available():
            return
        try:
            for g in guides:
                index_guide(g)
        except Exception as e:  # 색인 실패가 저장을 막지 않게
            self.message_user(request, f"임베딩 색인 실패(키워드 검색으로 대체됨): {e}", level="warning")


from django.utils import timezone  # noqa: E402

from apps.core.services import notify  # noqa: E402

from .models import Complaint  # noqa: E402


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("title", "body")

    def save_model(self, request, obj, form, change):
        """답변/상태가 바뀌면 접수자에게 알림"""
        notify_user = False
        if change:
            old = Complaint.objects.get(pk=obj.pk)
            notify_user = old.status != obj.status or old.answer != obj.answer
        if obj.answer and not obj.answered_at:
            obj.answered_at = timezone.now()
        super().save_model(request, obj, form, change)
        if notify_user:
            notify(obj.user, "complaint", f"민원 상태가 '{obj.get_status_display()}'(으)로 변경되었어요", obj.title, complaint_id=obj.id)


@admin.register(ChatTurn)
class ChatTurnAdmin(admin.ModelAdmin):
    """챗봇 답변 검토: 신고·👎 피드백 필터"""

    list_display = ("id", "role", "short_text", "feedback", "reported", "created_at")
    list_filter = ("reported", "feedback", "role")
    search_fields = ("text", "feedback_reason")

    @admin.display(description="내용")
    def short_text(self, obj):
        return obj.text[:60]
