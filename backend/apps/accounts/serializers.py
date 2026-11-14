import re

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.core.models import Region

from .models import Company, User


class CompanySerializer(serializers.ModelSerializer):
    business_number = serializers.CharField(max_length=20, help_text="사업자등록번호 (하이픈 허용, 숫자 10자리)")

    class Meta:
        model = Company
        fields = ("id", "name", "business_number", "representative", "address", "is_agency", "description", "is_verified")
        read_only_fields = ("id", "is_verified")

    def validate_business_number(self, value):
        digits = re.sub(r"\D", "", value)
        if len(digits) != 10:
            raise serializers.ValidationError("사업자등록번호는 숫자 10자리여야 합니다.")
        qs = Company.objects.filter(business_number=digits)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("이미 등록된 사업자등록번호입니다.")
        return digits


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    region = serializers.SlugRelatedField(
        slug_field="code", queryset=Region.objects.all(), required=False, allow_null=True,
        help_text="거주지역 코드 (예: 44130)",
    )
    company = CompanySerializer(required=False, help_text="role=employer 일 때 필수")

    class Meta:
        model = User
        fields = (
            "id", "username", "password", "role", "name", "email", "phone", "nationality",
            "preferred_language", "visa_type", "region", "company",
        )

    def validate_preferred_language(self, value):
        if value not in settings.SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(f"지원 언어: {', '.join(settings.SUPPORTED_LANGUAGES)}")
        return value

    def validate(self, attrs):
        if attrs.get("role") == User.Role.EMPLOYER:
            if not attrs.get("company"):
                raise serializers.ValidationError({"company": "사업주는 사업장 정보가 필요합니다."})
        else:
            attrs.pop("company", None)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        company = validated_data.pop("company", None)
        user = User.objects.create_user(**validated_data)
        if company:
            Company.objects.create(owner=user, **company)
        return user


class UserSerializer(serializers.ModelSerializer):
    region = serializers.SlugRelatedField(
        slug_field="code", queryset=Region.objects.all(), required=False, allow_null=True
    )
    company = CompanySerializer(read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "username", "role", "name", "email", "phone", "nationality", "preferred_language",
            "visa_type", "region", "profile_image", "temperature", "review_count", "company",
            "email_verified", "phone_verified", "notifications_enabled",
        )
        read_only_fields = ("id", "username", "role", "temperature", "review_count", "email_verified", "phone_verified")

    def validate_preferred_language(self, value):
        if value not in settings.SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(f"지원 언어: {', '.join(settings.SUPPORTED_LANGUAGES)}")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("현재 비밀번호가 일치하지 않습니다.")
        return value


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
