from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from billing.models import BillingCustomer, BillingProvider
from webhooks.models import WebhookProcessingStatus
from webhooks.stripe.client import fetch_invoice, fetch_payment_method, fetch_subscription
from webhooks.stripe.constants import STRIPE_SUPPORTED_EVENTS
from webhooks.stripe.customers import sync_customer_from_customer_object, sync_payment_method_snapshot
from webhooks.stripe.emails import (
    send_checkout_success_email,
    send_invoice_payment_failed_email,
    send_subscription_expired_email,
)
from webhooks.stripe.invoices import upsert_invoice_from_invoice_object
from webhooks.stripe.resolver import (
    resolve_company_for_checkout_session,
    resolve_company_for_customer,
    resolve_company_for_invoice,
    resolve_company_for_subscription,
)
from webhooks.stripe.subscriptions import upsert_subscription_from_subscription_object
from webhooks.stripe.utils import get_customer_id, obj_get

logger = logging.getLogger(__name__)


def handle_checkout_session_completed(session_obj):
    company = resolve_company_for_checkout_session(session_obj)
    if not company:
        raise ValueError("Could not resolve company for checkout session")

    customer_id = get_customer_id(session_obj)
    if customer_id:
        sync_customer_from_customer_object(
            company,
            {
                "id": customer_id,
                "email": obj_get(obj_get(session_obj, "customer_details", {}), "email", "") or "",
                "name": obj_get(obj_get(session_obj, "customer_details", {}), "name", "") or "",
                "metadata": obj_get(session_obj, "metadata", {}) or {},
            },
        )

    subscription = None
    subscription_id = obj_get(session_obj, "subscription", "") or ""
    if subscription_id:
        subscription_obj = fetch_subscription(subscription_id)
        if subscription_obj:
            subscription = upsert_subscription_from_subscription_object(subscription_obj, company)

    invoice = None
    invoice_id = obj_get(session_obj, "invoice", "") or ""
    if invoice_id:
        invoice_obj = fetch_invoice(invoice_id)
        if invoice_obj:
            invoice = upsert_invoice_from_invoice_object(invoice_obj, company)

    return {
        "company": company,
        "subscription": subscription,
        "invoice": invoice,
    }


def handle_customer_event(customer_obj):
    company = resolve_company_for_customer(customer_obj)
    if not company:
        return {"company": None, "customer": None}

    customer = sync_customer_from_customer_object(company, customer_obj)

    return {
        "company": company,
        "customer": customer,
    }


def handle_subscription_event(subscription_obj):
    company = resolve_company_for_subscription(subscription_obj)
    if not company:
        raise ValueError("Could not resolve company for subscription")

    subscription = upsert_subscription_from_subscription_object(subscription_obj, company)

    return {
        "company": company,
        "subscription": subscription,
    }


def handle_invoice_event(invoice_obj):
    company = resolve_company_for_invoice(invoice_obj)
    if not company:
        raise ValueError("Could not resolve company for invoice")

    invoice = upsert_invoice_from_invoice_object(invoice_obj, company)

    customer_id = get_customer_id(invoice_obj)
    payment_method_id = obj_get(invoice_obj, "default_payment_method", "") or ""

    if customer_id and payment_method_id:
        billing_customer = BillingCustomer.objects.filter(
            provider=BillingProvider.STRIPE,
            provider_customer_id=customer_id,
            company=company,
        ).first()

        if billing_customer:
            payment_method = fetch_payment_method(payment_method_id)
            if payment_method:
                sync_payment_method_snapshot(billing_customer, payment_method)

    return {
        "company": company,
        "invoice": invoice,
    }


def handle_payment_method_event(payment_method_obj, event_type: str):
    customer_id = obj_get(payment_method_obj, "customer", "") or ""
    if not customer_id:
        return {}

    billing_customer = BillingCustomer.objects.filter(
        provider=BillingProvider.STRIPE,
        provider_customer_id=customer_id,
    ).first()

    if not billing_customer:
        return {}

    if event_type == "payment_method.detached":
        sync_payment_method_snapshot(billing_customer, None)
    else:
        sync_payment_method_snapshot(billing_customer, payment_method_obj)

    return {
        "company": billing_customer.company,
        "customer": billing_customer,
    }


def send_billing_event_email(*, event_type: str, data_object, result: dict) -> None:
    company = result.get("company")
    subscription = result.get("subscription")
    invoice = result.get("invoice")

    if not company:
        return

    if event_type in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
    }:
        if not subscription:
            return

        fallback_email = obj_get(
            obj_get(data_object, "customer_details", {}),
            "email",
            "",
        ) or ""

        send_checkout_success_email(
            company=company,
            subscription=subscription,
            fallback_email=fallback_email,
        )
        return

    if event_type in {
        "checkout.session.async_payment_failed",
        "invoice.payment_failed",
    }:
        if not invoice:
            return

        fallback_email = ""
        if getattr(invoice, "customer", None) and invoice.customer.email:
            fallback_email = invoice.customer.email

        send_invoice_payment_failed_email(
            company=company,
            invoice=invoice,
            fallback_email=fallback_email,
        )
        return

    if event_type == "customer.subscription.deleted":
        if not subscription:
            return

        send_subscription_expired_email(
            company=company,
            subscription=subscription,
        )


@transaction.atomic
def process_stripe_event_record(webhook_event):
    event_type = webhook_event.event_type or ""
    payload = webhook_event.payload or {}
    data_object = ((payload.get("data") or {}).get("object") or {})

    webhook_event.status = WebhookProcessingStatus.PROCESSING
    webhook_event.processing_attempts = (webhook_event.processing_attempts or 0) + 1
    webhook_event.failure_reason = ""
    webhook_event.save(
        update_fields=[
            "status",
            "processing_attempts",
            "failure_reason",
            "updated_at",
        ]
    )

    try:
        if event_type not in STRIPE_SUPPORTED_EVENTS:
            webhook_event.status = WebhookProcessingStatus.IGNORED
            webhook_event.processed_at = timezone.now()
            webhook_event.failure_reason = "Unsupported Stripe event type."
            webhook_event.save(
                update_fields=[
                    "status",
                    "processed_at",
                    "failure_reason",
                    "updated_at",
                ]
            )
            return webhook_event

        result: dict = {}

        if event_type.startswith("checkout.session"):
            result = handle_checkout_session_completed(data_object)

        elif event_type.startswith("customer.subscription"):
            result = handle_subscription_event(data_object)

        elif event_type.startswith("invoice"):
            result = handle_invoice_event(data_object)

        elif event_type.startswith("customer"):
            result = handle_customer_event(data_object)

        elif event_type.startswith("payment_method"):
            result = handle_payment_method_event(data_object, event_type)

        send_billing_event_email(
            event_type=event_type,
            data_object=data_object,
            result=result,
        )

        webhook_event.status = WebhookProcessingStatus.PROCESSED
        webhook_event.processed_at = timezone.now()
        webhook_event.failed_at = None
        webhook_event.failure_reason = ""
        webhook_event.save(
            update_fields=[
                "status",
                "processed_at",
                "failed_at",
                "failure_reason",
                "updated_at",
            ]
        )

        return webhook_event

    except Exception as exc:
        logger.exception("Stripe webhook processing failed")

        webhook_event.status = WebhookProcessingStatus.FAILED
        webhook_event.failed_at = timezone.now()
        webhook_event.failure_reason = str(exc)
        webhook_event.save(
            update_fields=[
                "status",
                "failed_at",
                "failure_reason",
                "updated_at",
            ]
        )

        raise