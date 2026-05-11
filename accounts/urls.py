from django.urls import path

from .views.staff import StaffListView,StaffRoleUpdateView, StaffPermissionUpdateView, StaffRemoveView
from .views.companies import MyCompaniesView
from .views.dealerships import (
    DealershipCreateView,
    DealershipDetailView,
    DealershipListView,
    DealershipUpdateView,
)
urlpatterns = [
    
    path("companies", MyCompaniesView.as_view(), name="accounts-me-companies"),
    
    #staff
    path("staff/", StaffListView.as_view(), name="accounts-staff-list"),
    path("staff/<uuid:member_id>/role/", StaffRoleUpdateView.as_view(), name="accounts-staff-role"),
    path("staff/<uuid:member_id>/permissions/", StaffPermissionUpdateView.as_view(), name="accounts-staff-permissions"),
    path("staff/<uuid:member_id>/", StaffRemoveView.as_view(), name="accounts-staff-remove"),
    
    # Dealerships
    path("dealerships/", DealershipListView.as_view(), name="accounts-dealership-list"),
    path("dealerships/create/", DealershipCreateView.as_view(), name="accounts-dealership-create"),
    path("dealerships/<uuid:dealership_id>/", DealershipDetailView.as_view(), name="accounts-dealership-detail"),
    path("dealerships/<uuid:dealership_id>/update/", DealershipUpdateView.as_view(), name="accounts-dealership-update"),
    
]
