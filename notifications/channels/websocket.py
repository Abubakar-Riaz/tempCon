# notifications/channels/websocket.py

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from notifications.models import Notification, NotificationDelivery


def get_notification_group_name(*, dealership_public_id: str, user_public_id: str) -> str:
    dealership_id = str(dealership_public_id).replace(":", "_").replace("/", "_")
    user_id = str(user_public_id).replace(":", "_").replace("/", "_")
    return f"notifications_{dealership_id}_{user_id}"


def serialize_notification_for_websocket(notification: Notification) -> dict:
    return {
        "id": str(notification.public_id),
        "type": notification.type,
        "category": notification.category,
        "priority": notification.priority,
        "title": notification.title,
        "body": notification.body,
        "entity_type": notification.entity_type,
        "entity_public_id": notification.entity_public_id,
        "target_url": notification.target_url,
        "is_read": notification.is_read,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "metadata": notification.metadata or {},
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def send_websocket_delivery(*, delivery: NotificationDelivery) -> NotificationDelivery:
    notification = delivery.notification
    channel_layer = get_channel_layer()

    if channel_layer is None:
        delivery.mark_failed("Django Channels layer is not configured.")
        return delivery

    group_name = get_notification_group_name(
        dealership_public_id=notification.dealership.public_id,
        user_public_id=notification.recipient.public_id,
    )

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "send_notification",
            "payload": {
                "type": "notification.created",
                "notification": serialize_notification_for_websocket(notification),
            },
        },
    )

    delivery.metadata = {
        **(delivery.metadata or {}),
        "group_name": group_name,
    }
    delivery.mark_sent()
    return delivery