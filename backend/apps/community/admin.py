from django.contrib import admin

from .models import Comment, CompanionPost, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "category", "region", "is_hidden", "created_at")
    list_filter = ("category", "is_hidden", "region")
    search_fields = ("title", "body")


admin.site.register(Comment)
admin.site.register(CompanionPost)
