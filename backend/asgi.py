import os
import django

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Point to your settings and initialize Django first
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

# HTTP app
django_asgi_app = get_asgi_application()

# Import websocket routing only AFTER django.setup()
from backend.routing import websocket_urlpatterns  # noqa: E402

# ASGI application
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
