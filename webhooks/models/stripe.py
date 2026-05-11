# webhooks/models/stripe.py

from __future__ import annotations

from django.db import models

from .base import WebhookEvent


class StripeWebhookEvent(WebhookEvent):
    customer_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    subscription_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    invoice_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    checkout_session_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    class Meta:
        db_table = "webhooks_stripe_webhook_event"
        verbose_name = "Stripe Webhook Event"
        verbose_name_plural = "Stripe Webhook Events"