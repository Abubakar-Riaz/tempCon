# notifications/services/delivery.py

from __future__ import annotations

import logging

from django.utils import timezone

from notifications.constants import NotificationChannels, NotificationDeliveryStatuses
from notifications.models import Notification, NotificationDelivery
from notifications.services.preferences import (
    get_or_create_notification_preferences,
    should_send_email_notification,
    should_send_websocket_notification,
)

logger = logging.getLogger(__name__)


def create_delivery(
    *,
    notification: Notification,
    channel: str,
    status: str = NotificationDeliveryStatuses.PENDING,
    metadata: dict | None = None,
    failure_reason: str = "",
) -> NotificationDelivery:
    return NotificationDelivery.objects.create(
        notification=notification,
        channel=channel,
        status=status,
        sent_at=timezone.now() if status == NotificationDeliveryStatuses.SENT else None,
        failure_reason=failure_reason,
        metadata=metadata or {},
    )


def create_delivery_rows_for_notification(
    *,
    notification: Notification,
    include_websocket: bool = True,
    include_email: bool = True,
    include_push: bool = False,
) -> list[NotificationDelivery]:
    preferences = get_or_create_notification_preferences(
        user=notification.recipient,
        dealership=notification.dealership,
    )

    deliveries = [
        create_delivery(
            notification=notification,
            channel=NotificationChannels.IN_APP,
            status=NotificationDeliveryStatuses.SENT,
        )
    ]

    if include_websocket:
        if should_send_websocket_notification(
            preferences=preferences,
            notification_type=notification.type,
            category=notification.category,
        ):
            deliveries.append(
                create_delivery(
                    notification=notification,
                    channel=NotificationChannels.WEBSOCKET,
                )
            )
        else:
            deliveries.append(
                create_delivery(
                    notification=notification,
                    channel=NotificationChannels.WEBSOCKET,
                    status=NotificationDeliveryStatuses.SKIPPED,
                    failure_reason="WebSocket notifications disabled by preferences.",
                )
            )

    if include_email:
        if should_send_email_notification(
            preferences=preferences,
            dealership=notification.dealership,
            recipient=notification.recipient,
            notification_type=notification.type,
            category=notification.category,
            priority=notification.priority,
            notification=notification,
        ):
            deliveries.append(
                create_delivery(
                    notification=notification,
                    channel=NotificationChannels.EMAIL,
                )
            )
        else:
            deliveries.append(
                create_delivery(
                    notification=notification,
                    channel=NotificationChannels.EMAIL,
                    status=NotificationDeliveryStatuses.SKIPPED,
                    failure_reason=(
                        "Email notifications disabled by preferences, importance settings, "
                        "or subscription feature gate."
                    ),
                )
            )
    if include_push:
        deliveries.append(
            create_delivery(
                notification=notification,
                channel=NotificationChannels.PUSH,
                status=NotificationDeliveryStatuses.SKIPPED,
                failure_reason="Push notifications are not implemented yet.",
            )
        )

    return deliveries


def dispatch_delivery(*, delivery: NotificationDelivery) -> NotificationDelivery:
    if delivery.status != NotificationDeliveryStatuses.PENDING:
        return delivery

    try:
        if delivery.channel == NotificationChannels.WEBSOCKET:
            from notifications.channels.websocket import send_websocket_delivery
            return send_websocket_delivery(delivery=delivery)

        if delivery.channel == NotificationChannels.EMAIL:
            from notifications.channels.email import send_email_delivery
            return send_email_delivery(delivery=delivery)

        if delivery.channel == NotificationChannels.PUSH:
            from notifications.channels.push import send_push_delivery
            return send_push_delivery(delivery=delivery)

        if delivery.channel == NotificationChannels.IN_APP:
            from notifications.channels.in_app import send_in_app_delivery
            return send_in_app_delivery(delivery=delivery)

        delivery.mark_skipped(f"Unsupported channel: {delivery.channel}")
        return delivery

    except Exception as exc:
        logger.exception("Notification delivery failed.")
        delivery.mark_failed(str(exc))
        return delivery


def dispatch_notification_deliveries(*, notification: Notification) -> list[NotificationDelivery]:
    deliveries = notification.deliveries.filter(
        status=NotificationDeliveryStatuses.PENDING,
    ).select_related(
        "notification",
        "notification__recipient",
        "notification__dealership",
    )

    return [dispatch_delivery(delivery=delivery) for delivery in deliveries]


def prepare_notification_deliveries(
    *,
    notification: Notification,
    include_websocket: bool = True,
    include_email: bool = True,
    include_push: bool = False,
    dispatch_now: bool = True,
) -> list[NotificationDelivery]:
    deliveries = create_delivery_rows_for_notification(
        notification=notification,
        include_websocket=include_websocket,
        include_email=include_email,
        include_push=include_push,
    )

    if dispatch_now:
        dispatch_notification_deliveries(notification=notification)

    return deliveries