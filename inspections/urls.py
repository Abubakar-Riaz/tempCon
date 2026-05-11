# inspections/urls.py

from django.urls import path

from inspections.views.inspections import VehicleInspectionView
from inspections.views.attachments import InspectionItemAttachmentView
from inspections.views.trades import TradesListView

urlpatterns = [
    path(
        "trades/",
        TradesListView.as_view(),
        name="inspections-trades-list",
    ),
    path(
        "vehicles/<uuid:vehicle_id>/",
        VehicleInspectionView.as_view(),
        name="vehicle-inspection-detail",
    ),
    path(
        "items/<uuid:item_id>/attachments/",
        InspectionItemAttachmentView.as_view(),
        name="inspection-item-attachments",
    ),
]