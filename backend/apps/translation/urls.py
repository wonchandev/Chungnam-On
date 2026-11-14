from django.urls import path

from . import views

urlpatterns = [
    path("translate/text/", views.TranslateTextView.as_view(), name="translate-text"),
    path("translate/voice/", views.VoiceTranslateView.as_view(), name="translate-voice"),
    path("translate/image/", views.ImageTranslateView.as_view(), name="translate-image"),
    path("languages/", views.LanguageListView.as_view(), name="language-list"),
    path("phrases/", views.PhraseListView.as_view(), name="phrase-list"),
    path("courses/", views.CourseListView.as_view(), name="course-list"),
    path("courses/mine/", views.MyCourseListView.as_view(), name="course-mine"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course-detail"),
    path("courses/<int:pk>/enroll/", views.CourseEnrollView.as_view(), name="course-enroll"),
]
