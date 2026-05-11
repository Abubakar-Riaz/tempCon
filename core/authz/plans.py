from __future__ import annotations

from billing.models import PlanCode
from core.authz.features import Features
from core.authz.limits import Limits


PLAN_DEFAULT_FEATURES: dict[str, dict[str, bool]] = {
    PlanCode.STARTER: {
        Features.MULTI_DEALERSHIP: False,
        Features.STAFF_INVITES: True,
        Features.VENDOR_INVITES: False,
        Features.CUSTOM_ROLES: False,
        Features.INVENTORY: True,
        Features.CSV_IMPORT: True,
        Features.AUCTION_IMPORT: False,
        Features.VHR: True,
        Features.INSPECTIONS: True,
        Features.HAMMER: True,
        Features.BUYING: True,
        Features.RECON: True,
        Features.VENDORS: False,
        Features.NOTIFICATIONS: True,
        Features.AUDIT_LOGS: False,
        Features.BILLING: True,
        Features.PRIORITY_SUPPORT: False,
    },
    PlanCode.GROWTH: {
        Features.MULTI_DEALERSHIP: True,
        Features.STAFF_INVITES: True,
        Features.VENDOR_INVITES: True,
        Features.CUSTOM_ROLES: False,
        Features.INVENTORY: True,
        Features.CSV_IMPORT: True,
        Features.AUCTION_IMPORT: True,
        Features.VHR: True,
        Features.INSPECTIONS: True,
        Features.HAMMER: True,
        Features.BUYING: True,
        Features.RECON: True,
        Features.VENDORS: True,
        Features.NOTIFICATIONS: True,
        Features.AUDIT_LOGS: True,
        Features.BILLING: True,
        Features.PRIORITY_SUPPORT: False,
    },
    PlanCode.BUSINESS: {
        Features.MULTI_DEALERSHIP: True,
        Features.STAFF_INVITES: True,
        Features.VENDOR_INVITES: True,
        Features.CUSTOM_ROLES: True,
        Features.INVENTORY: True,
        Features.CSV_IMPORT: True,
        Features.AUCTION_IMPORT: True,
        Features.VHR: True,
        Features.INSPECTIONS: True,
        Features.HAMMER: True,
        Features.BUYING: True,
        Features.RECON: True,
        Features.VENDORS: True,
        Features.NOTIFICATIONS: True,
        Features.AUDIT_LOGS: True,
        Features.BILLING: True,
        Features.PRIORITY_SUPPORT: False,
    },
    PlanCode.ENTERPRISE: {
        Features.MULTI_DEALERSHIP: True,
        Features.STAFF_INVITES: True,
        Features.VENDOR_INVITES: True,
        Features.CUSTOM_ROLES: True,
        Features.INVENTORY: True,
        Features.CSV_IMPORT: True,
        Features.AUCTION_IMPORT: True,
        Features.VHR: True,
        Features.INSPECTIONS: True,
        Features.HAMMER: True,
        Features.BUYING: True,
        Features.RECON: True,
        Features.VENDORS: True,
        Features.NOTIFICATIONS: True,
        Features.AUDIT_LOGS: True,
        Features.BILLING: True,
        Features.PRIORITY_SUPPORT: True,
    },
}


PLAN_DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    PlanCode.STARTER: {
        Limits.MAX_USERS: 3,
        Limits.MAX_DEALERSHIPS: 1,
        Limits.MAX_VEHICLES_PER_MONTH: 100,
        Limits.MAX_ACTIVE_VEHICLES: 250,
        Limits.MAX_STORAGE_BYTES: 1_073_741_824,
        Limits.MAX_ATTACHMENTS_PER_VEHICLE: 20,
        Limits.MAX_VENDOR_USERS: 0,
        Limits.MAX_TRADES: 10,
    },
    PlanCode.GROWTH: {
        Limits.MAX_USERS: 10,
        Limits.MAX_DEALERSHIPS: 3,
        Limits.MAX_VEHICLES_PER_MONTH: 500,
        Limits.MAX_ACTIVE_VEHICLES: 1_000,
        Limits.MAX_STORAGE_BYTES: 5_368_709_120,
        Limits.MAX_ATTACHMENTS_PER_VEHICLE: 50,
        Limits.MAX_VENDOR_USERS: 25,
        Limits.MAX_TRADES: 25,
    },
    PlanCode.BUSINESS: {
        Limits.MAX_USERS: 30,
        Limits.MAX_DEALERSHIPS: 10,
        Limits.MAX_VEHICLES_PER_MONTH: 2_500,
        Limits.MAX_ACTIVE_VEHICLES: 5_000,
        Limits.MAX_STORAGE_BYTES: 21_474_836_480,
        Limits.MAX_ATTACHMENTS_PER_VEHICLE: 100,
        Limits.MAX_VENDOR_USERS: 100,
        Limits.MAX_TRADES: 100,
    },
    PlanCode.ENTERPRISE: {
        Limits.MAX_USERS: 250,
        Limits.MAX_DEALERSHIPS: 100,
        Limits.MAX_VEHICLES_PER_MONTH: 50_000,
        Limits.MAX_ACTIVE_VEHICLES: 100_000,
        Limits.MAX_STORAGE_BYTES: 107_374_182_400,
        Limits.MAX_ATTACHMENTS_PER_VEHICLE: 250,
        Limits.MAX_VENDOR_USERS: 1_000,
        Limits.MAX_TRADES: 500,
    },
}


PLAN_DEFAULTS: dict[str, dict[str, dict]] = {
    code: {
        "features": PLAN_DEFAULT_FEATURES[code],
        "limits": PLAN_DEFAULT_LIMITS[code],
    }
    for code in PLAN_DEFAULT_FEATURES
}


def get_plan_default_features(plan_code: str) -> dict[str, bool]:
    return dict(PLAN_DEFAULT_FEATURES.get(plan_code, {}))


def get_plan_default_limits(plan_code: str) -> dict[str, int]:
    return dict(PLAN_DEFAULT_LIMITS.get(plan_code, {}))


def get_plan_defaults(plan_code: str) -> dict[str, dict]:
    return {
        "features": get_plan_default_features(plan_code),
        "limits": get_plan_default_limits(plan_code),
    }