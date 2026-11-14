from django.contrib import admin

from .models import Application, Bookmark, JobCategory, JobPost, JobPostTranslation, Review


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "order")


class TranslationInline(admin.TabularInline):
    model = JobPostTranslation
    extra = 0


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ("title", "company", "category", "region", "pay_type", "pay_amount", "status", "is_urgent")
    list_filter = ("status", "category", "region", "is_urgent")
    search_fields = ("title", "company__name")
    inlines = [TranslationInline]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("job", "applicant", "status", "created_at")
    list_filter = ("status",)


admin.site.register(Bookmark)
admin.site.register(Review)
