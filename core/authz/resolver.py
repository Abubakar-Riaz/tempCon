#core/authz/resolver.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.authz.limits import Limits
from core.authz.permissions import Permissions
from core.authz.roles import ROLE_DEFAULT_PERMISSIONS
from core.authz.settings import AUTHZ_ENABLE_SUBSCRIPTION_CHECKS


@dataclass
class AccessContext:
    user: Any
    membership: Any
    dealership: Any
    company: Any
    subscription: Any | None
    permissions: set[str] = field(default_factory=set)
    features: dict[str, Any] = field(default_factory=dict)
    limits: dict[str, Any] = field(default_factory=dict)


def _normalize_permission_overrides(overrides: dict | None) -> tuple[set[str], set[str]]:
    overrides = overrides or {}

    allow: set[str] = set()
    deny: set[str] = set()

    if "allow" in overrides or "deny" in overrides:
        return set(overrides.get("allow") or []), set(overrides.get("deny") or [])

    for key, value in overrides.items():
        if value is True:
            allow.add(key)
        elif value is False:
            deny.add(key)

    return allow, deny


def get_membership_permissions(membership) -> set[str]:
    if membership is None:
        return set()

    role = getattr(membership, "role", "") or ""
    base = set(ROLE_DEFAULT_PERMISSIONS.get(role, set()))

    allow, deny = _normalize_permission_overrides(
        getattr(membership, "permission_overrides", None)
    )

    base |= allow
    base -= deny

    if getattr(membership, "is_company_owner", False):
        base |= {
            Permissions.MANAGE_COMPANY,
            Permissions.VIEW_COMPANY,
            Permissions.MANAGE_BILLING,
            Permissions.VIEW_BILLING,
            Permissions.CREATE_DEALERSHIP,
            Permissions.DELETE_DEALERSHIP,
        }

    return base


def get_subscription_features(subscription) -> dict[str, Any]:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return {
            "multi_dealership": True,
            "team_management": True,
            "inventory": True,
            "csv_import": True,
            "auction_import": True,
            "vhr": True,
            "inspections": True,
            "hammer": True,
            "buying": True,
            "recon": True,
            "vendors": True,
            "notifications": True,
            "audit_logs": True,
            "billing": True,
        }

    if subscription is None:
        return {}

    if hasattr(subscription, "get_effective_features"):
        return subscription.get_effective_features() or {}

    return {}


def get_subscription_limits(subscription) -> dict[str, Any]:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return {
            Limits.MAX_USERS: 10,
            Limits.MAX_DEALERSHIPS: 3,
        }

    if subscription is None:
        return {}

    if hasattr(subscription, "get_effective_limits"):
        return subscription.get_effective_limits() or {}

    return {}


def build_access_context(*, user, membership, dealership, subscription=None) -> AccessContext:
    company = getattr(dealership, "company", None) if dealership is not None else None

    permissions = get_membership_permissions(membership)
    features = get_subscription_features(subscription)
    limits = get_subscription_limits(subscription)

    return AccessContext(
        user=user,
        membership=membership,
        dealership=dealership,
        company=company,
        subscription=subscription,
        permissions=permissions,
        features=features,
        limits=limits,
    )


def get_effective_permissions(membership, subscription=None) -> set[str]:
    return get_membership_permissions(membership)


def has_permission(ctx: AccessContext, permission: str) -> bool:
    return permission in ctx.permissions


def has_any_permission(ctx: AccessContext, *permissions: str) -> bool:
    return any(permission in ctx.permissions for permission in permissions)


def has_feature(ctx: AccessContext, feature: str) -> bool:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return True

    return bool(ctx.features.get(feature, False))


def get_limit(ctx: AccessContext, limit_key: str, default=None):
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return None

    return ctx.limits.get(limit_key, default)


def can_access_vehicle(ctx: AccessContext, vehicle) -> bool:
    if vehicle is None:
        return False

    return getattr(vehicle, "dealership_id", None) == getattr(ctx.dealership, "id", None)


def can_access_recon_work_item(ctx: AccessContext, work_item) -> bool:
    if work_item is None:
        return False

    recon_case = getattr(work_item, "recon_case", None)
    vehicle = getattr(recon_case, "vehicle", None)

    if not can_access_vehicle(ctx, vehicle):
        return False

    if has_permission(ctx, Permissions.MANAGE_RECON):
        return True

    if not has_permission(ctx, Permissions.VIEW_VENDOR_WORK):
        return False

    assigned_vendor_id = getattr(work_item, "assigned_vendor_id", None)
    membership_id = getattr(ctx.membership, "id", None)

    return assigned_vendor_id is not None and assigned_vendor_id == membership_id