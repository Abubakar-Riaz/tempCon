from django.urls import path
from inventory.views.folders import (
    FolderListView,
    FolderCreateView,
)
from inventory.views.vehicle_history import VehicleHistoryView
from inventory.views.vehicles import (
    FolderVehicleListCreateView,
    FolderVehicleImportView,
    VehicleDetailUpdateView,
    VehicleImportTemplateDownloadView,
)
from inventory.views.vehicle_phase import VehiclePhaseAdvanceView
from inventory.views.vhr import VehicleVHRView
from inventory.views.vin_scanner import (
    VehicleVinSearchView,
    VehicleVinQuickAddView,
)

urlpatterns = [
    
    # VIN scanner
    path(
        "vin-search/",
        VehicleVinSearchView.as_view(),
        name="inventory_vin_search",
    ),
    path(
        "vin-quick-add/",
        VehicleVinQuickAddView.as_view(),
        name="inventory_vin_quick_add",
    ),
    # Folders
    path(
        "folders/",
        FolderListView.as_view(),
        name="inventory-folders-list",
    ),
    path(
        "folders/create/",
        FolderCreateView.as_view(),
        name="inventory-folder-create",
    ),

    # Vehicles (list/create)
    path(
        "folders/<uuid:folder_id>/vehicles/",
        FolderVehicleListCreateView.as_view(),
        name="inventory-folder-vehicles",
    ),
    path(
        "folders/<uuid:folder_id>/vehicles/import/",
        FolderVehicleImportView.as_view(),
        name="inventory-folder-vehicles-import",
    ),
    path(
        "vehicles/<uuid:vehicle_id>/",
        VehicleDetailUpdateView.as_view(),
        name="inventory-vehicle-detail-update",
    ),
    path(
        "vehicles/template.csv",
        VehicleImportTemplateDownloadView.as_view(),
        name="inventory-vehicles-template",
    ),
        path(
        "vehicles/<uuid:vehicle_id>/history/",
        VehicleHistoryView.as_view(),
        name="inventory-vehicle-history",
    ),
    path(
        "vehicles/<uuid:vehicle_id>/vhr/",
        VehicleVHRView.as_view(),
        name="inventory-vehicle-vhr",
    ),
    # Phase Advance
    path(
        "vehicles/<uuid:vehicle_id>/phase/advance/",
        VehiclePhaseAdvanceView.as_view(),
        name="inventory-vehicle-phase-advance",
    ),
]
