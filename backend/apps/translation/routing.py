from django.urls import path

from .consumers import VoiceTranslationConsumer

websocket_urlpatterns = [path("ws/translate/voice/", VoiceTranslationConsumer.as_asgi())]
