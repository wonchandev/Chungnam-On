from django.urls import path

from . import views

urlpatterns = [
    path("admin-info/dashboard/", views.DashboardView.as_view(), name="admin-dashboard"),
    path("admin-info/guides/", views.GuideListView.as_view(), name="guide-list"),
    path("admin-info/guides/<int:pk>/", views.GuideDetailView.as_view(), name="guide-detail"),
    path("admin-info/frequent/", views.FrequentGuideView.as_view(), name="guide-frequent"),
    path("admin-info/popular/", views.PopularGuideView.as_view(), name="guide-popular"),
    path("admin-info/complaints/", views.ComplaintListCreateView.as_view(), name="complaint-list"),
    path("admin-info/complaints/<int:pk>/", views.ComplaintDetailView.as_view(), name="complaint-detail"),
    path("assistant/chat/", views.AssistantChatView.as_view(), name="assistant-chat"),
    path("assistant/conversations/", views.ConversationListView.as_view(), name="assistant-conversations"),
    path("assistant/conversations/<int:pk>/", views.ConversationDetailView.as_view(), name="assistant-conversation"),
    path("assistant/documents/templates/", views.DocumentTemplateListView.as_view(), name="assistant-doc-templates"),
    path("assistant/documents/", views.DocumentDraftView.as_view(), name="assistant-doc-draft"),
]
