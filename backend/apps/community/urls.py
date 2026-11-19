from django.urls import path

from . import views

urlpatterns = [
    path("community/posts/", views.PostListCreateView.as_view(), name="post-list"),
    path("community/posts/<int:pk>/", views.PostDetailView.as_view(), name="post-detail"),
    path("community/posts/<int:pk>/like/", views.PostLikeView.as_view(), name="post-like"),
    path("community/posts/<int:pk>/comments/", views.CommentListCreateView.as_view(), name="post-comments"),
    path("community/comments/<int:pk>/", views.CommentDeleteView.as_view(), name="comment-delete"),
    path("community/companions/", views.CompanionListCreateView.as_view(), name="companion-list"),
    path("community/companions/<int:pk>/", views.CompanionDetailView.as_view(), name="companion-detail"),
    path("community/companions/<int:pk>/join/", views.CompanionJoinView.as_view(), name="companion-join"),
    path("community/companions/<int:pk>/participants/", views.CompanionParticipantListView.as_view(), name="companion-participants"),
]
