from django.contrib import admin

from .models import AdminGuide, AdminGuideTranslation


class GuideTranslationInline(admin.StackedInline):
    model = AdminGuideTranslation
    extra = 0


@admin.register(AdminGuide)
class AdminGuideAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_published", "view_count", "updated_at")
    list_filter = ("category", "is_published")
    search_fields = ("title", "body")
    inlines = [GuideTranslationInline]


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
