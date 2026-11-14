from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Company, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("충남온", {"fields": ("role", "name", "nationality", "preferred_language", "phone", "visa_type",
                              "region", "profile_image", "temperature", "review_count")}),
    )
    list_display = ("username", "name", "role", "nationality", "temperature", "is_staff")
    list_filter = UserAdmin.list_filter + ("role",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "business_number", "is_agency", "is_verified")
    list_filter = ("is_agency", "is_verified")
    search_fields = ("name", "business_number")
