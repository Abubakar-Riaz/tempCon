# vendors/urls.py

from django.urls import path

from vendors.views.vendors import DealershipVendorsListView
from vendors.views.work_items import (
    VendorWorkItemsListView,
    VendorWorkItemCompleteView,
    VendorWorkItemAttachmentUploadView,
)

urlpatterns = [
    path(
        "",
        DealershipVendorsListView.as_view(),
        name="dealership-vendors-list",
    ),
    path(
        "vehicles/<uuid:vehicle_id>/work-items/",
        VendorWorkItemsListView.as_view(),
        name="vendor-vehicle-workitems-list",
    ),
    path(
        "work-items/<uuid:work_item_id>/complete/",
        VendorWorkItemCompleteView.as_view(),
        name="vendor-workitem-complete",
    ),
    path(
        "work-items/<uuid:work_item_id>/attachments/",
        VendorWorkItemAttachmentUploadView.as_view(),
        name="vendor-workitem-attachment-upload",
    ),
]