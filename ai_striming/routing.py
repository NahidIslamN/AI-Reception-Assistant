from django.urls import path

from .consumers import RealtimeVoiceConsumer

websocket_urlpatterns = [
    path("ws/ai-striming/voice/", RealtimeVoiceConsumer.as_asgi()),
]
