from __future__ import annotations

from dataclasses import dataclass

import stripe
from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from billing.models import (
    BillingCustomer,
    BillingInvoice,
    BillingProvider,
    CompanySubscription,
    SubscriptionPlan,
    SubscriptionPlanPrice,
)
from inventory.models import Vehicle


class BillingError(Exception):
    pass


@dataclass
class BillingOverview:
    customer: BillingCustomer | None
    subscription: CompanySubscription | None
    payment_method: dict
    usage: dict
    features: dict
    limits: dict


def get_public_plans():
    return (
        SubscriptionPlan.objects
        .filter(is_active=True, is_public=True)
        .prefetch_related("prices")
        .order_by("sort_order", "created_at")
    )


def get_featured_plan():
    return (
        get_public_plans()
        .filter(code__in=["growth", "business"])
        .first()
    )


def get_company_subscription(company):
    return (
        CompanySubscription.objects
        .select_related("plan", "plan_price")
        .filter(company=company)
        .first()
    )


def get_company_billing_customer(company):
    return (
        BillingCustomer.objects
        .filter(company=company, provider=BillingProvider.STRIPE)
        .first()
    )


def get_company_invoices(company):
    return (
        BillingInvoice.objects
        .filter(company=company)
        .select_related("customer", "subscription")
        .order_by("-created_at")
    )


def get_company_usage(company) -> dict:
    now = timezone.now()

    vehicles_this_month = Vehicle.objects.filter(
        company=company,
        created_at__year=now.year,
        created_at__month=now.month,
    ).count()

    active_vehicles = Vehicle.objects.filter(company=company).exclude(
        status="complete",
    ).count()

    dealerships = company.dealerships.filter(is_active=True).count()
    users = company.memberships.filter(status="active").values("user_id").distinct().count()

    return {
        "vehicles_this_month": vehicles_this_month,
        "active_vehicles": active_vehicles,
        "dealerships": dealerships,
        "users": users,
    }


def get_billing_overview(company) -> BillingOverview:
    subscription = get_company_subscription(company)
    customer = get_company_billing_customer(company)

    payment_method = {}
    if customer:
        payment_method = {
            "type": customer.default_payment_method_type,
            "brand": customer.default_payment_method_brand,
            "last4": customer.default_payment_method_last4,
            "exp_month": customer.default_payment_method_exp_month,
            "exp_year": customer.default_payment_method_exp_year,
            "updated_at": customer.default_payment_method_updated_at,
        }

    return BillingOverview(
        customer=customer,
        subscription=subscription,
        payment_method=payment_method,
        usage=get_company_usage(company),
        features=subscription.get_effective_features() if subscription else {},
        limits=subscription.get_effective_limits() if subscription else {},
    )


def _stripe_client():
    api_key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not api_key:
        raise BillingError("Stripe is not configured.")

    stripe.api_key = api_key
    return stripe


def get_or_create_billing_customer(*, company, user) -> BillingCustomer:
    existing = get_company_billing_customer(company)
    if existing:
        return existing

    client = _stripe_client()

    customer = client.Customer.create(
        email=company.email or getattr(user, "email", ""),
        name=company.legal_name or company.name,
        metadata={
            "company_id": company.public_id,
        },
    )

    return BillingCustomer.objects.create(
        company=company,
        provider=BillingProvider.STRIPE,
        provider_customer_id=customer["id"],
        email=customer.get("email") or "",
        name=customer.get("name") or "",
        metadata={
            "stripe_customer": customer,
        },
    )


def create_checkout_session(
    *,
    company,
    user,
    plan_code: str,
    interval: str,
    success_url: str,
    cancel_url: str,
) -> str:
    plan_price = (
        SubscriptionPlanPrice.objects
        .select_related("plan")
        .filter(
            plan__code=plan_code,
            plan__is_active=True,
            plan__is_public=True,
            interval=interval,
            provider=BillingProvider.STRIPE,
            is_active=True,
            is_public=True,
        )
        .first()
    )

    if not plan_price:
        raise BillingError("Invalid plan or billing interval.")

    customer = get_or_create_billing_customer(company=company, user=user)
    client = _stripe_client()

    session = client.checkout.Session.create(
        mode="subscription",
        customer=customer.provider_customer_id,
        line_items=[
            {
                "price": plan_price.stripe_price_id,
                "quantity": 1,
            }
        ],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "company_id": company.public_id,
            "plan_code": plan_price.plan.code,
            "plan_price_id": plan_price.public_id,
        },
        subscription_data={
            "metadata": {
                "company_id": company.public_id,
                "plan_code": plan_price.plan.code,
                "plan_price_id": plan_price.public_id,
            }
        },
    )

    return session["url"]


def create_portal_session(*, company, return_url: str) -> str:
    customer = get_company_billing_customer(company)

    if not customer or not customer.provider_customer_id:
        raise BillingError("Billing customer does not exist.")

    client = _stripe_client()

    session = client.billing_portal.Session.create(
        customer=customer.provider_customer_id,
        return_url=return_url,
    )

    return session["url"]