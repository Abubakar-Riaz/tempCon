from __future__ import annotations

import json

import stripe
from django.conf import settings
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from webhooks.models import StripeWebhookEvent, WebhookProcessingStatus, WebhookProvider
from webhooks.stripe.processor import process_stripe_event_record
from webhooks.stripe.utils import extract_stripe_identifiers


class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        raw_body = request.body or b""
        signature = request.headers.get("Stripe-Signature", "") or ""

        if not signature:
            return Response({"detail": "Missing Stripe signature"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = stripe.Webhook.construct_event(
                payload=raw_body,
                sig_header=signature,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except ValueError:
            return Response({"detail": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"detail": "Invalid signature"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            payload = {}

        event_id = event.get("id", "") or payload.get("id", "")
        event_type = event.get("type", "") or payload.get("type", "")

        identifiers = extract_stripe_identifiers(payload)

        defaults = {
            "provider": WebhookProvider.STRIPE,
            "status": WebhookProcessingStatus.RECEIVED,
            "event_type": event_type,
            "signature": signature,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "payload": payload,
            **identifiers,
        }

        try:
            webhook_event, created = StripeWebhookEvent.objects.get_or_create(
                provider=WebhookProvider.STRIPE,
                provider_event_id=event_id,
                defaults=defaults,
            )
        except IntegrityError:
            webhook_event = StripeWebhookEvent.objects.get(
                provider=WebhookProvider.STRIPE,
                provider_event_id=event_id,
            )
            created = False

        if not created:
            return Response({"detail": "Already received"}, status=status.HTTP_200_OK)

        try:
            process_stripe_event_record(webhook_event)
        except Exception:
            pass

        return Response({"detail": "OK"}, status=status.HTTP_200_OK)