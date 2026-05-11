# inspections/routing.py

from django.urls import path

from inspections.consumers import InspectionRoomConsumer

websocket_urlpatterns = [
    path(
        "ws/inspections/vehicles/<uuid:vehicle_id>/",
        InspectionRoomConsumer.as_asgi(),
    ),
]