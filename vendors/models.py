# vendors/models.py

from django.conf import settings
from django.db import models

from accounts.models import Company, Dealership
from core.models.base import PublicIDModel, TimestampedModel


class VendorTrade(PublicIDModel, TimestampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_trades",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="vendor_trades",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        related_name="vendor_trades",
    )

    trade = models.ForeignKey(
        "inspections.Trade",
        on_delete=models.CASCADE,
        related_name="vendor_trades",
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "vendors_vendor_trade"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["dealership", "is_active"]),
            models.Index(fields=["trade", "is_active"]),
            models.Index(fields=["dealership", "trade", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dealership", "trade"],
                name="uniq_vendor_trade_per_user_dealership_trade",
            ),
        ]

    def __str__(self):
        return f"{self.user} / {self.dealership} / {self.trade}"

    def save(self, *args, **kwargs):
        if self.dealership_id:
            self.company_id = self.dealership.company_id
        super().save(*args, **kwargs)