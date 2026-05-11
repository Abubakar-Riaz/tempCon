# recon/urls.py

from django.urls import path

from recon.views.recon import ReconCaseView, ReconStatusView
from recon.views.work_items import AssignVendorView

urlpatterns = [
    path(
        "vehicles/<uuid:vehicle_id>/recon/",
        ReconCaseView.as_view(),
        name="recon-case-detail",
    ),
    path(
        "vehicles/<uuid:vehicle_id>/recon/status/",
        ReconStatusView.as_view(),
        name="recon-status-update",
    ),
    path(
        "assign-vendor/<uuid:work_item_id>/",
        AssignVendorView.as_view(),
        name="recon-assign-vendor",
    ),
]