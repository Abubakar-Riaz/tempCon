from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import Company, Dealership


class KPIScope(models.TextChoices):
    PLATFORM = "PLATFORM", _("Platform")     # platform-wide metrics
    COMPANY = "COMPANY", _("Company")        # per-company metrics
    DEALERSHIP = "DEALERSHIP", _("Dealership")  # per-dealership metrics


class KPIShard(models.Model):
    """
    Pre-aggregated metric snapshot for dashboards.
    Store anything: counts, breakdowns, timeseries points, etc., in 'value'.
    """
    scope = models.CharField(max_length=16, choices=KPIScope.choices)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name="kpi_shards")
    dealership = models.ForeignKey(Dealership, on_delete=models.CASCADE, null=True, blank=True, related_name="kpi_shards")

    key = models.CharField(max_length=128)      # e.g., "vehicles.by_phase", "recon.throughput", "billing.invoices", "platform.active_companies"
    value = models.JSONField()                  # numeric or structured payload
    as_of_date = models.DateField()             # the date the metric represents
    granularity = models.CharField(max_length=8, default="D")  # "D" (daily), "W", "M"
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-as_of_date", "-computed_at")
        unique_together = ("scope", "company", "dealership", "key", "as_of_date")
        indexes = [
            models.Index(fields=("scope", "as_of_date")),
            models.Index(fields=("company", "as_of_date")),
            models.Index(fields=("dealership", "as_of_date")),
            models.Index(fields=("key", "as_of_date")),
        ]

    def __str__(self):
        return f"{self.scope}:{self.key}@{self.as_of_date}"


class DashboardCardConfig(models.Model):
    """
    Optional: controls which KPI keys appear for which audience and in what order.
    Useful for Platform Admin, Company Admin, Location Admin screens.
    """
    audience = models.CharField(max_length=32)  # e.g., "PLATFORM_ADMIN", "COMPANY_ADMIN", "LOCATION_ADMIN"
    scope = models.CharField(max_length=16, choices=KPIScope.choices)
    key = models.CharField(max_length=128)      # must match KPIShard.key
    label = models.CharField(max_length=128, blank=True)
    order_index = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)  # chart type, units, thresholds, etc.
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("audience", "scope", "key")
        ordering = ("audience", "scope", "order_index")

    def __str__(self):
        return f"{self.audience}:{self.scope}:{self.key}"
