from django.urls import path

from .views import (
    BlockListView, BlockView, NotificationListView, NotificationReadView, RegionListView, RegionSearchView,
    ReportCreateView, UnreadCountView,
)

urlpatterns = [
    path("regions/", RegionListView.as_view(), name="region-list"),
    path("regions/search/", RegionSearchView.as_view(), name="region-search"),
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/unread-count/", UnreadCountView.as_view(), name="notification-unread"),
    path("notifications/read-all/", NotificationReadView.as_view(), name="notification-read-all"),
    path("notifications/<int:pk>/read/", NotificationReadView.as_view(), name="notification-read"),
    path("reports/", ReportCreateView.as_view(), name="report-create"),
    path("blocks/", BlockListView.as_view(), name="block-list"),
    path("blocks/<int:user_id>/", BlockView.as_view(), name="block"),
]
