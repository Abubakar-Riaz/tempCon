# notifications/routing.py

from django.urls import path

from notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path(
        "ws/dealerships/<uuid:dealership_id>/notifications/",
        NotificationConsumer.as_asgi(),
    ),
]