from __future__ import annotations

from accounts.models import Company
from billing.models import (
    BillingCustomer,
    BillingProvider,
    CompanySubscription,
    SubscriptionPlanPrice,
)


def get_company_by_public_id(public_id: str) -> Company | None:
    if not public_id:
        return None

    return Company.objects.filter(public_id=public_id, is_active=True).first()


def get_billing_customer_by_provider_customer_id(customer_id: str) -> BillingCustomer | None:
    if not customer_id:
        return None

    return (
        BillingCustomer.objects
        .select_related("company")
        .filter(
            provider=BillingProvider.STRIPE,
            provider_customer_id=customer_id,
        )
        .first()
    )


def get_subscription_by_provider_subscription_id(subscription_id: str) -> CompanySubscription | None:
    if not subscription_id:
        return None

    return (
        CompanySubscription.objects
        .select_related("company", "plan", "plan_price")
        .filter(
            provider=BillingProvider.STRIPE,
            provider_subscription_id=subscription_id,
        )
        .first()
    )


def get_plan_price_by_stripe_price_id(stripe_price_id: str) -> SubscriptionPlanPrice | None:
    if not stripe_price_id:
        return None

    return (
        SubscriptionPlanPrice.objects
        .select_related("plan")
        .filter(
            provider=BillingProvider.STRIPE,
            stripe_price_id=stripe_price_id,
            is_active=True,
        )
        .first()
    )