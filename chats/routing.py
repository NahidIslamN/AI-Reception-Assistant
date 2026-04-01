from django.urls import path
from chats import consumers

websocket_urlpatterns = [
    path(r'ws/asc/chats/', consumers.UpdateChatConsumerMessageGet.as_asgi()),
    path(r'ws/asc/notifications/', consumers.NotificationConsumer.as_asgi()),
    
]
