# hammer/urls.py

from django.urls import path

from hammer.views.hammer import VehicleHammerView

urlpatterns = [
    path(
        "vehicles/<uuid:vehicle_id>/",
        VehicleHammerView.as_view(),
        name="vehicle-hammer",
    ),
]