from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("auth/", include("authx.urls")),
    path("audit/", include("audit.urls")),    
    path("billing/", include("billing.urls")),
    path("buying/", include("buying.urls")),
    # path("dashboards/", include("dashboards.urls")),
    path("hammer/", include("hammer.urls")),
    path("invites/", include("invites.urls")),
    path("inventory/", include("inventory.urls")),
    path("inspections/", include("inspections.urls")),
    path("notifications/", include("notifications.urls")),
    path("recon/", include("recon.urls")),
    path("vendors/", include("vendors.urls")),



]