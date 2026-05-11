from __future__ import annotations

from typing import Any

from django.utils import timezone

from billing.models import BillingCustomer, BillingProvider
from webhooks.stripe.queries import get_billing_customer_by_provider_customer_id
from webhooks.stripe.utils import get_metadata, obj_get


def upsert_billing_customer(
    *,
    company,
    customer_id: str,
    email: str = "",
    name: str = "",
    metadata: dict | None = None,
) -> BillingCustomer:
    customer, _ = BillingCustomer.objects.update_or_create(
        company=company,
        defaults={
            "provider": BillingProvider.STRIPE,
            "provider_customer_id": customer_id,
            "email": email or "",
            "name": name or "",
            "metadata": metadata or {},
        },
    )

    return customer


def sync_payment_method_snapshot(
    billing_customer: BillingCustomer,
    payment_method_obj: Any | None,
) -> BillingCustomer:
    if not payment_method_obj:
        billing_customer.default_payment_method_id = ""
        billing_customer.default_payment_method_type = ""
        billing_customer.default_payment_method_brand = ""
        billing_customer.default_payment_method_last4 = ""
        billing_customer.default_payment_method_exp_month = None
        billing_customer.default_payment_method_exp_year = None
        billing_customer.default_payment_method_updated_at = timezone.now()
    else:
        card = obj_get(payment_method_obj, "card")

        billing_customer.default_payment_method_id = obj_get(payment_method_obj, "id", "") or ""
        billing_customer.default_payment_method_type = obj_get(payment_method_obj, "type", "") or ""
        billing_customer.default_payment_method_brand = obj_get(card, "brand", "") if card else ""
        billing_customer.default_payment_method_last4 = obj_get(card, "last4", "") if card else ""
        billing_customer.default_payment_method_exp_month = obj_get(card, "exp_month") if card else None
        billing_customer.default_payment_method_exp_year = obj_get(card, "exp_year") if card else None
        billing_customer.default_payment_method_updated_at = timezone.now()

    billing_customer.save(
        update_fields=[
            "default_payment_method_id",
            "default_payment_method_type",
            "default_payment_method_brand",
            "default_payment_method_last4",
            "default_payment_method_exp_month",
            "default_payment_method_exp_year",
            "default_payment_method_updated_at",
            "updated_at",
        ]
    )

    return billing_customer


def sync_customer_from_customer_object(company, customer_obj: Any) -> BillingCustomer:
    return upsert_billing_customer(
        company=company,
        customer_id=obj_get(customer_obj, "id", "") or "",
        email=obj_get(customer_obj, "email", "") or "",
        name=obj_get(customer_obj, "name", "") or "",
        metadata=get_metadata(customer_obj),
    )


def sync_customer_from_customer_id(company, customer_id: str) -> BillingCustomer:
    existing = get_billing_customer_by_provider_customer_id(customer_id)

    if existing and existing.company_id == company.id:
        return existing

    return upsert_billing_customer(
        company=company,
        customer_id=customer_id,
    )