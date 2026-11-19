from django.contrib import admin

from apps.jobs.models import JobPost

from .models import Block, Notification, Region, Report


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "level", "parent")
    list_filter = ("level",)
    search_fields = ("name", "code")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("target_type", "target_id", "reason", "status", "reporter", "created_at")
    list_filter = ("status", "target_type", "reason")
    actions = ["hide_targets", "reject_reports"]

    @admin.action(description="선택한 신고 대상을 블라인드 처리(공고/게시글/댓글)하고 처리 완료로 표시")
    def hide_targets(self, request, queryset):
        from apps.community.models import Comment, Post

        models = {"job": JobPost, "post": Post, "comment": Comment}
        for r in queryset:
            model = models.get(r.target_type)
            if model:
                model.objects.filter(pk=r.target_id).update(is_hidden=True)
        queryset.update(status=Report.Status.RESOLVED)

    @admin.action(description="선택한 신고를 반려")
    def reject_reports(self, request, queryset):
        queryset.update(status=Report.Status.REJECTED)


admin.site.register(Notification)
admin.site.register(Block)
