from __future__ import annotations

from typing import Any

from django.utils import timezone

from billing.models import BillingProvider, CompanySubscription
from webhooks.stripe.customers import sync_payment_method_snapshot, upsert_billing_customer
from webhooks.stripe.queries import get_plan_price_by_stripe_price_id
from webhooks.stripe.utils import (
    dt_from_unix,
    get_customer_id,
    get_metadata,
    get_price_id_from_subscription,
    get_product_id_from_subscription,
    map_subscription_status,
    obj_get,
)


def upsert_subscription_from_subscription_object(subscription_obj: Any, company) -> CompanySubscription:
    customer_id = get_customer_id(subscription_obj)

    billing_customer = None
    if customer_id:
        billing_customer = upsert_billing_customer(
            company=company,
            customer_id=customer_id,
            metadata=get_metadata(subscription_obj),
        )

    stripe_price_id = get_price_id_from_subscription(subscription_obj)
    plan_price = get_plan_price_by_stripe_price_id(stripe_price_id)

    if not plan_price:
        raise ValueError(f"Could not map Stripe price '{stripe_price_id}' to SubscriptionPlanPrice")

    defaults = {
        "company": company,
        "plan": plan_price.plan,
        "plan_price": plan_price,
        "provider": BillingProvider.STRIPE,
        "provider_product_id": get_product_id_from_subscription(subscription_obj),
        "provider_price_id": stripe_price_id,
        "status": map_subscription_status(obj_get(subscription_obj, "status")),
        "starts_at": dt_from_unix(obj_get(subscription_obj, "start_date")) or timezone.now(),
        "ends_at": dt_from_unix(obj_get(subscription_obj, "ended_at")),
        "current_period_start": dt_from_unix(obj_get(subscription_obj, "current_period_start")),
        "current_period_end": dt_from_unix(obj_get(subscription_obj, "current_period_end")),
        "cancel_at_period_end": bool(obj_get(subscription_obj, "cancel_at_period_end", False)),
        "cancel_at": dt_from_unix(obj_get(subscription_obj, "cancel_at")),
        "canceled_at": dt_from_unix(obj_get(subscription_obj, "canceled_at")),
        "ended_at": dt_from_unix(obj_get(subscription_obj, "ended_at")),
        "metadata": get_metadata(subscription_obj),
    }

    subscription, created = CompanySubscription.objects.get_or_create(
        provider=BillingProvider.STRIPE,
        provider_subscription_id=obj_get(subscription_obj, "id", "") or "",
        defaults=defaults,
    )

    if not created:
        dirty_fields: list[str] = []

        for field, value in defaults.items():
            if getattr(subscription, field) != value:
                setattr(subscription, field, value)
                dirty_fields.append(field)

        if dirty_fields:
            dirty_fields.append("updated_at")
            subscription.save(update_fields=dirty_fields)

    default_payment_method = obj_get(subscription_obj, "default_payment_method")
    if billing_customer and default_payment_method:
        sync_payment_method_snapshot(billing_customer, default_payment_method)

    return subscription