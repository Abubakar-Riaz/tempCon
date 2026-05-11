from __future__ import annotations

import stripe
from django.conf import settings


def _configure_stripe():
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def fetch_subscription(subscription_id: str):
    if not subscription_id:
        return None

    client = _configure_stripe()

    return client.Subscription.retrieve(
        subscription_id,
        expand=["default_payment_method", "items.data.price"],
    )


def fetch_invoice(invoice_id: str):
    if not invoice_id:
        return None

    client = _configure_stripe()

    return client.Invoice.retrieve(
        invoice_id,
        expand=["lines.data.price"],
    )


def fetch_payment_method(payment_method_id: str):
    if not payment_method_id:
        return None

    client = _configure_stripe()

    return client.PaymentMethod.retrieve(payment_method_id)