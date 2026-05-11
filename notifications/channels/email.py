# notifications/channels/email.py

from __future__ import annotations

from core.email import send_email
from django.conf import settings
from django.template.loader import render_to_string

from notifications.models import NotificationDelivery


def send_email_delivery(*, delivery: NotificationDelivery) -> NotificationDelivery:
    notification = delivery.notification
    recipient = notification.recipient

    if not recipient.email:
        delivery.mark_skipped("Recipient has no email address.")
        return delivery

    frontend_base_url = getattr(settings, "FRONTEND_BASE_URL", "").rstrip("/")
    target_url = notification.target_url or ""
    full_target_url = f"{frontend_base_url}{target_url}" if target_url.startswith("/") else target_url

    html = render_to_string(
        "emails/notifications/notification.html",
        {
            "notification": notification,
            "recipient": recipient,
            "dealership": notification.dealership,
            "target_url": full_target_url,
            "app_name": "BuyCon",
        },
    )

    send_email(
        to_email=recipient.email,
        from_email="notifications@buycon.com",
        from_name="BuyCon Notifications",
        subject=notification.title,
        html=html,
    )

    delivery.metadata = {
        **(delivery.metadata or {}),
        "recipient_email": recipient.email,
    }
    delivery.mark_sent()
    return delivery