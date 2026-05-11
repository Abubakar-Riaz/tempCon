from __future__ import annotations

from typing import Any

from billing.models import BillingCustomer, BillingInvoice, BillingProvider, CompanySubscription
from webhooks.stripe.customers import upsert_billing_customer
from webhooks.stripe.utils import (
    amount_from_cents,
    dt_from_unix,
    extract_invoice_line_items,
    get_customer_id,
    get_metadata,
    get_subscription_id,
    json_safe,
    map_invoice_status,
    obj_get,
)


def upsert_invoice_from_invoice_object(invoice_obj: Any, company) -> BillingInvoice | None:
    invoice_id = obj_get(invoice_obj, "id", "") or ""
    if not invoice_id:
        return None

    customer_id = get_customer_id(invoice_obj)
    subscription_id = get_subscription_id(invoice_obj)

    billing_customer = None
    if customer_id:
        billing_customer = BillingCustomer.objects.filter(
            company=company,
            provider=BillingProvider.STRIPE,
            provider_customer_id=customer_id,
        ).first()

        if not billing_customer:
            billing_customer = upsert_billing_customer(
                company=company,
                customer_id=customer_id,
                metadata=get_metadata(invoice_obj),
            )

    subscription = None
    if subscription_id:
        subscription = CompanySubscription.objects.filter(
            company=company,
            provider=BillingProvider.STRIPE,
            provider_subscription_id=subscription_id,
        ).first()

    defaults = {
        "company": company,
        "customer": billing_customer,
        "subscription": subscription,
        "provider": BillingProvider.STRIPE,
        "provider_customer_id": customer_id,
        "provider_subscription_id": subscription_id,
        "provider_payment_intent_id": obj_get(invoice_obj, "payment_intent", "") or "",
        "provider_hosted_invoice_url": obj_get(invoice_obj, "hosted_invoice_url", "") or "",
        "provider_invoice_pdf_url": obj_get(invoice_obj, "invoice_pdf", "") or "",
        "invoice_number": obj_get(invoice_obj, "number", "") or "",
        "currency": (obj_get(invoice_obj, "currency", "") or "USD").upper(),
        "status": map_invoice_status(obj_get(invoice_obj, "status")),
        "subtotal": amount_from_cents(obj_get(invoice_obj, "subtotal")),
        "tax": amount_from_cents(obj_get(invoice_obj, "tax")),
        "total": amount_from_cents(obj_get(invoice_obj, "total")),
        "amount_paid": amount_from_cents(obj_get(invoice_obj, "amount_paid")),
        "amount_remaining": amount_from_cents(obj_get(invoice_obj, "amount_remaining")),
        "billing_reason": obj_get(invoice_obj, "billing_reason", "") or "",
        "collection_method": obj_get(invoice_obj, "collection_method", "") or "",
        "period_start": dt_from_unix(obj_get(invoice_obj, "period_start")),
        "period_end": dt_from_unix(obj_get(invoice_obj, "period_end")),
        "due_at": dt_from_unix(obj_get(invoice_obj, "due_date")),
        "paid_at": dt_from_unix(obj_get(obj_get(invoice_obj, "status_transitions", {}), "paid_at")),
        "voided_at": dt_from_unix(obj_get(obj_get(invoice_obj, "status_transitions", {}), "voided_at")),
        "metadata": json_safe(get_metadata(invoice_obj)),
        "raw_line_items": json_safe(extract_invoice_line_items(invoice_obj)),
    }

    invoice, created = BillingInvoice.objects.get_or_create(
        provider=BillingProvider.STRIPE,
        provider_invoice_id=invoice_id,
        defaults=defaults,
    )

    if created:
        return invoice

    dirty_fields: list[str] = []

    for field, value in defaults.items():
        if getattr(invoice, field) != value:
            setattr(invoice, field, value)
            dirty_fields.append(field)

    if dirty_fields:
        dirty_fields.append("updated_at")
        invoice.save(update_fields=dirty_fields)

    return invoice