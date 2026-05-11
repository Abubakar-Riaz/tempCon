from django.urls import path
from dashboards.metrics import DashboardsCompanyMetricsView

urlpatterns = [
    path(
        "companies/<uuid:company_id>/metrics",
        DashboardsCompanyMetricsView.as_view(),
        name="dashboards.company.metrics",
    ),
]
