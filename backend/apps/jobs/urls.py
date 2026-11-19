from django.urls import path

from . import map_views, views

urlpatterns = [
    # 공고
    path("jobs/", views.JobListCreateView.as_view(), name="job-list"),
    path("jobs/mine/", views.MyJobListView.as_view(), name="job-mine"),
    path("jobs/urgent/", views.UrgentJobListView.as_view(), name="job-urgent"),
    path("jobs/popular-categories/", views.PopularCategoryView.as_view(), name="job-popular-categories"),
    path("jobs/bookmarks/", views.BookmarkListView.as_view(), name="job-bookmarks"),
    path("jobs/recommended/", views.RecommendedJobView.as_view(), name="job-recommended"),
    path("jobs/ticker/", views.JobTickerView.as_view(), name="job-ticker"),
    path("jobs/recent/", views.RecentJobListView.as_view(), name="job-recent"),
    path("jobs/popular-searches/", views.PopularSearchView.as_view(), name="job-popular-searches"),
    # 지도
    path("jobs/map/", map_views.MapMarkerView.as_view(), name="job-map"),
    path("jobs/map/clusters/", map_views.MapClusterView.as_view(), name="job-map-clusters"),
    path("jobs/nearby/", map_views.NearbyJobView.as_view(), name="job-nearby"),
    path("jobs/<int:pk>/", views.JobDetailView.as_view(), name="job-detail"),
    path("jobs/<int:pk>/duplicate/", views.JobDuplicateView.as_view(), name="job-duplicate"),
    path("jobs/<int:pk>/close/", views.JobCloseView.as_view(), name="job-close"),
    path("jobs/<int:pk>/apply/", views.ApplyView.as_view(), name="job-apply"),
    path("jobs/<int:pk>/applications/", views.JobApplicantListView.as_view(), name="job-applicants"),
    path("jobs/<int:pk>/bookmark/", views.BookmarkView.as_view(), name="job-bookmark"),
    path("jobs/<int:pk>/reviews/", views.JobReviewCreateView.as_view(), name="job-review"),
    # 지원
    path("applications/mine/", views.MyApplicationListView.as_view(), name="application-mine"),
    path("applications/<int:pk>/", views.ApplicationDetailView.as_view(), name="application-detail"),
    path("applications/<int:pk>/check-in/", views.CheckInView.as_view(), name="application-check-in"),
    path("applications/<int:pk>/complete/", views.CompleteView.as_view(), name="application-complete"),
    # 인력사무소
    path("agencies/", views.AgencyListView.as_view(), name="agency-list"),
    path("agencies/<int:pk>/", views.AgencyDetailView.as_view(), name="agency-detail"),
    # 기타
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("users/<int:pk>/reputation/", views.ReputationView.as_view(), name="user-reputation"),
]
