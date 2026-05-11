from __future__ import annotations

from typing import Any

from webhooks.stripe.queries import (
    get_billing_customer_by_provider_customer_id,
    get_company_by_public_id,
    get_subscription_by_provider_subscription_id,
)
from webhooks.stripe.utils import get_customer_id, get_metadata, get_subscription_id, obj_get


def find_company_from_metadata(metadata: dict):
    public_id = (
        metadata.get("company_id")
        or metadata.get("company_public_id")
        or metadata.get("company")
        or ""
    )

    return get_company_by_public_id(public_id)


def resolve_company_for_checkout_session(session_obj: Any):
    company = find_company_from_metadata(get_metadata(session_obj))
    if company:
        return company

    client_reference_id = obj_get(session_obj, "client_reference_id", "") or ""
    company = get_company_by_public_id(client_reference_id)
    if company:
        return company

    billing_customer = get_billing_customer_by_provider_customer_id(
        get_customer_id(session_obj)
    )

    return billing_customer.company if billing_customer else None


def resolve_company_for_customer(customer_obj: Any):
    company = find_company_from_metadata(get_metadata(customer_obj))
    if company:
        return company

    billing_customer = get_billing_customer_by_provider_customer_id(
        obj_get(customer_obj, "id", "") or ""
    )

    return billing_customer.company if billing_customer else None


def resolve_company_for_subscription(subscription_obj: Any):
    company = find_company_from_metadata(get_metadata(subscription_obj))
    if company:
        return company

    billing_customer = get_billing_customer_by_provider_customer_id(
        get_customer_id(subscription_obj)
    )
    if billing_customer:
        return billing_customer.company

    subscription = get_subscription_by_provider_subscription_id(
        obj_get(subscription_obj, "id", "") or ""
    )

    return subscription.company if subscription else None


def resolve_company_for_invoice(invoice_obj: Any):
    company = find_company_from_metadata(get_metadata(invoice_obj))
    if company:
        return company

    billing_customer = get_billing_customer_by_provider_customer_id(
        get_customer_id(invoice_obj)
    )
    if billing_customer:
        return billing_customer.company

    subscription = get_subscription_by_provider_subscription_id(
        get_subscription_id(invoice_obj)
    )

    return subscription.company if subscription else None