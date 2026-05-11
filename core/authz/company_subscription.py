# core/authz/company_subscription.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.authz.settings import AUTHZ_ENABLE_SUBSCRIPTION_CHECKS


@dataclass(frozen=True)
class CompanySubscriptionContext:
    company: Any
    subscription: Any | None
    features: dict[str, Any]
    limits: dict[str, Any]


def get_company_subscription(company) -> Any | None:
    if company is None:
        return None

    return getattr(company, "subscription", None)


def is_subscription_active(subscription) -> bool:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return True

    if subscription is None:
        return False

    if hasattr(subscription, "is_active_effective"):
        return bool(subscription.is_active_effective)

    status = getattr(subscription, "status", None)
    return status in {"trialing", "active"}


def get_subscription_features_for_company(company) -> dict[str, Any]:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return {
            "notifications": True,
            "email_notifications": True,
        }

    subscription = get_company_subscription(company)

    if not is_subscription_active(subscription):
        return {}

    if hasattr(subscription, "get_effective_features"):
        return subscription.get_effective_features() or {}

    return {}


def get_subscription_limits_for_company(company) -> dict[str, Any]:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return {}

    subscription = get_company_subscription(company)

    if not is_subscription_active(subscription):
        return {}

    if hasattr(subscription, "get_effective_limits"):
        return subscription.get_effective_limits() or {}

    return {}


def build_company_subscription_context(company) -> CompanySubscriptionContext:
    subscription = get_company_subscription(company)

    return CompanySubscriptionContext(
        company=company,
        subscription=subscription,
        features=get_subscription_features_for_company(company),
        limits=get_subscription_limits_for_company(company),
    )


def company_has_active_subscription(company) -> bool:
    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return True

    return is_subscription_active(get_company_subscription(company))


def company_has_feature(company, feature: str) -> bool:
    if not feature:
        return False

    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return True

    features = get_subscription_features_for_company(company)
    return bool(features.get(feature, False))


def get_company_limit(company, limit_key: str, default=None):
    if not limit_key:
        return default

    if not AUTHZ_ENABLE_SUBSCRIPTION_CHECKS:
        return None

    limits = get_subscription_limits_for_company(company)
    return limits.get(limit_key, default)


def get_company_plan(company):
    subscription = get_company_subscription(company)

    if subscription is None:
        return None

    return getattr(subscription, "plan", None)


def get_company_plan_code(company) -> str:
    plan = get_company_plan(company)

    if plan is None:
        return ""

    return getattr(plan, "code", "") or ""


def get_company_subscription_status(company) -> str:
    subscription = get_company_subscription(company)

    if subscription is None:
        return ""

    return getattr(subscription, "status", "") or ""