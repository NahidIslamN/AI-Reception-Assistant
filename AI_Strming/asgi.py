
import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from chats.routing import websocket_urlpatterns
from .custom_auth import CustomAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YourProjectName.settings')

# application = get_asgi_application()

# ASGI_APPLICATION = 'YourProjectName.asgi.application'



application = ProtocolTypeRouter(
    {
        'http':get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            CustomAuthMiddleware(
                URLRouter(
                    websocket_urlpatterns
                )
            )
        )
    }
)



