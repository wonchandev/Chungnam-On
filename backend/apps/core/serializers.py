from rest_framework import serializers

from .models import Region


class RegionSerializer(serializers.ModelSerializer):
    parent_code = serializers.CharField(source="parent.code", read_only=True, default=None)

    class Meta:
        model = Region
        fields = ("id", "code", "name", "name_en", "level", "parent_code", "lat", "lng")


from .models import Block, Notification, Report  # noqa: E402


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "data", "is_read", "created_at")


class ReportSerializer(serializers.ModelSerializer):
    target_type_label = serializers.CharField(source="get_target_type_display", read_only=True)
    reason_label = serializers.CharField(source="get_reason_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    class Meta:
        model = Report
        fields = ("id", "target_type", "target_type_label", "target_id", "reason", "reason_label", "detail", "status", "status_label", "created_at")
        read_only_fields = ("id", "status", "created_at")


class BlockSerializer(serializers.ModelSerializer):
    blocked_name = serializers.CharField(source="blocked.display_name", read_only=True)

    class Meta:
        model = Block
        fields = ("blocked", "blocked_name", "created_at")
