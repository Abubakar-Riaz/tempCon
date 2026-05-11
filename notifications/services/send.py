# notifications/services/send.py

from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction

from notifications.models import Notification
from notifications.registry import (
    get_default_category_for_type,
    get_default_priority_for_type,
    is_valid_notification_category,
    is_valid_notification_type,
)
from notifications.services.delivery import prepare_notification_deliveries
from notifications.services.preferences import (
    get_or_create_notification_preferences,
    should_create_in_app_notification,
)


@transaction.atomic
def send_notification(
    *,
    dealership,
    recipient,
    notification_type: str,
    title: str,
    body: str = "",
    actor=None,
    category: str | None = None,
    priority: str | None = None,
    entity_type: str = "",
    entity_public_id: str = "",
    target_url: str = "",
    metadata: dict | None = None,
    include_websocket: bool = True,
    include_email: bool = True,
    include_push: bool = False,
    dispatch_now: bool = True,
) -> Notification | None:
    if not is_valid_notification_type(notification_type):
        raise ValueError(f"Unknown notification type: {notification_type}")

    resolved_category = category or get_default_category_for_type(notification_type)
    resolved_priority = priority or get_default_priority_for_type(notification_type)

    if not is_valid_notification_category(resolved_category):
        raise ValueError(f"Unknown notification category: {resolved_category}")

    preferences = get_or_create_notification_preferences(
        user=recipient,
        dealership=dealership,
    )

    if not should_create_in_app_notification(
        preferences=preferences,
        notification_type=notification_type,
        category=resolved_category,
    ):
        return None

    notification = Notification.objects.create(
        dealership=dealership,
        recipient=recipient,
        actor=actor,
        type=notification_type,
        category=resolved_category,
        priority=resolved_priority,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_public_id=entity_public_id,
        target_url=target_url,
        metadata=metadata or {},
    )

    prepare_notification_deliveries(
        notification=notification,
        include_websocket=include_websocket,
        include_email=include_email,
        include_push=include_push,
        dispatch_now=dispatch_now,
    )

    return notification


def dedupe_recipients(users: Iterable) -> list:
    seen = set()
    result = []

    for user in users:
        if user is None:
            continue

        ident = getattr(user, "pk", None) or id(user)

        if ident in seen:
            continue

        seen.add(ident)
        result.append(user)

    return result


def send_notification_to_many(
    *,
    dealership,
    recipients: Iterable,
    notification_type: str,
    title: str,
    body: str = "",
    actor=None,
    category: str | None = None,
    priority: str | None = None,
    entity_type: str = "",
    entity_public_id: str = "",
    target_url: str = "",
    metadata: dict | None = None,
    include_websocket: bool = True,
    include_email: bool = True,
    include_push: bool = False,
    dispatch_now: bool = True,
) -> list[Notification]:
    notifications = []

    for recipient in dedupe_recipients(recipients):
        notification = send_notification(
            dealership=dealership,
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=body,
            actor=actor,
            category=category,
            priority=priority,
            entity_type=entity_type,
            entity_public_id=entity_public_id,
            target_url=target_url,
            metadata=metadata,
            include_websocket=include_websocket,
            include_email=include_email,
            include_push=include_push,
            dispatch_now=dispatch_now,
        )

        if notification:
            notifications.append(notification)

    return notifications