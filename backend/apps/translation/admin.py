from django.contrib import admin

from .models import TranslationCache


@admin.register(TranslationCache)
class TranslationCacheAdmin(admin.ModelAdmin):
    list_display = ("source_lang", "target_lang", "source_text", "created_at")
    search_fields = ("source_text", "translated_text")

from .models import CourseEnrollment, LanguageCourse, Phrase  # noqa: E402

admin.site.register(Phrase)
admin.site.register(LanguageCourse)
admin.site.register(CourseEnrollment)
