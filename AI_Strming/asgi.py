
import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from chats.routing import websocket_urlpatterns as chats_websocket_urlpatterns
from ai_striming.routing import websocket_urlpatterns as stream_websocket_urlpatterns
from .custom_auth import CustomAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Strming.settings')

# application = get_asgi_application()

# ASGI_APPLICATION = 'YourProjectName.asgi.application'



application = ProtocolTypeRouter(
    {
        'http':get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            CustomAuthMiddleware(
                URLRouter(
                    chats_websocket_urlpatterns + stream_websocket_urlpatterns
                )
            )
        )
    }
)



