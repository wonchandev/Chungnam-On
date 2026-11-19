from django.urls import path

from . import views

urlpatterns = [
    path("chat/quick-replies/", views.QuickReplyListView.as_view(), name="chat-quick-replies"),
    path("chat/rooms/", views.RoomListCreateView.as_view(), name="chat-rooms"),
    path("chat/rooms/<int:pk>/", views.RoomDetailView.as_view(), name="chat-room"),
    path("chat/rooms/<int:pk>/messages/", views.MessageListCreateView.as_view(), name="chat-messages"),
    path("chat/rooms/<int:pk>/call/", views.RoomCallView.as_view(), name="chat-call"),
    path("chat/rooms/<int:pk>/read/", views.RoomReadView.as_view(), name="chat-read"),
    path("chat/rooms/<int:pk>/translation/", views.RoomTranslationView.as_view(), name="chat-translation"),
]
