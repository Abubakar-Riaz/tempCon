# core/authz/features.py

from __future__ import annotations


class Features:
    MULTI_DEALERSHIP = "multi_dealership"
    CUSTOM_ROLES = "custom_roles"

    STAFF_INVITES = "staff_invites"
    VENDOR_INVITES = "vendor_invites"

    INVENTORY = "inventory"
    CSV_IMPORT = "csv_import"
    AUCTION_IMPORT = "auction_import"

    VHR = "vhr"
    INSPECTIONS = "inspections"
    HAMMER = "hammer"
    BUYING = "buying"
    RECON = "recon"
    VENDORS = "vendors"

    NOTIFICATIONS = "notifications"
    EMAIL_NOTIFICATIONS = "email_notifications"

    AUDIT_LOGS = "audit_logs"

    BILLING = "billing"
    PRIORITY_SUPPORT = "priority_support"

    @classmethod
    def all(cls) -> set[str]:
        return {
            value
            for key, value in cls.__dict__.items()
            if key.isupper() and isinstance(value, str)
        }