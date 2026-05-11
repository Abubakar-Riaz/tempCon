# buying/urls.py

from django.urls import path

from buying.views.buying import VehicleBuyingView

urlpatterns = [
    path(
        "vehicles/<uuid:vehicle_id>/buying/",
        VehicleBuyingView.as_view(),
        name="vehicle-buying",
    ),
]