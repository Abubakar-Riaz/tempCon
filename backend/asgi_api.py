# backend/asgi_api.py

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings.api")

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

from authx.channels_auth import CookieJWTAuthMiddlewareStack
from inspections.routing import websocket_urlpatterns as inspection_websocket_urlpatterns
from notifications.routing import websocket_urlpatterns as notification_websocket_urlpatterns


websocket_urlpatterns = [
    *notification_websocket_urlpatterns,
    *inspection_websocket_urlpatterns,
]


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            CookieJWTAuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        ),
    }
)