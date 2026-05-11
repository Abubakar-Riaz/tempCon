# notifications/services/preferences.py

from __future__ import annotations

from typing import Any

from core.authz.company_subscription import company_has_feature
from core.authz.features import Features
from notifications.constants import NotificationChannels, NotificationPriorities
from notifications.models import Notification, NotificationPreference
from notifications.registry import get_default_channels_for_category


def get_or_create_notification_preferences(*, user, dealership) -> NotificationPreference:
    preferences, _ = NotificationPreference.objects.get_or_create(
        user=user,
        dealership=dealership,
    )
    return preferences


def is_global_channel_enabled(*, preferences: NotificationPreference, channel: str) -> bool:
    if channel == NotificationChannels.IN_APP:
        return preferences.in_app_enabled

    if channel == NotificationChannels.WEBSOCKET:
        return preferences.websocket_enabled

    if channel == NotificationChannels.EMAIL:
        return preferences.email_enabled

    if channel == NotificationChannels.PUSH:
        return False

    return True


def _get_json_channel_override(*, data: dict[str, Any], key: str, channel: str) -> bool | None:
    value = data.get(key)

    if not isinstance(value, dict):
        return None

    if channel not in value:
        return None

    return bool(value[channel])


def get_channel_preference(
    *,
    preferences: NotificationPreference,
    notification_type: str,
    category: str,
    channel: str,
) -> bool:
    if not is_global_channel_enabled(preferences=preferences, channel=channel):
        return False

    type_override = _get_json_channel_override(
        data=preferences.type_preferences or {},
        key=notification_type,
        channel=channel,
    )

    if type_override is not None:
        return type_override

    category_override = _get_json_channel_override(
        data=preferences.category_preferences or {},
        key=category,
        channel=channel,
    )

    if category_override is not None:
        return category_override

    return bool(get_default_channels_for_category(category).get(channel, True))


def is_email_allowed_by_importance(
    *,
    preferences: NotificationPreference,
    priority: str,
) -> bool:
    if not preferences.email_important_only:
        return True

    return priority in {
        NotificationPriorities.HIGH,
        NotificationPriorities.CRITICAL,
    }


def is_email_feature_allowed(
    *,
    dealership,
    recipient,
    notification: Notification | None = None,
) -> bool:
    company = getattr(dealership, "company", None)

    return company_has_feature(
        company,
        Features.EMAIL_NOTIFICATIONS,
    )


def should_create_in_app_notification(*, preferences, notification_type: str, category: str) -> bool:
    return get_channel_preference(
        preferences=preferences,
        notification_type=notification_type,
        category=category,
        channel=NotificationChannels.IN_APP,
    )


def should_send_websocket_notification(*, preferences, notification_type: str, category: str) -> bool:
    return get_channel_preference(
        preferences=preferences,
        notification_type=notification_type,
        category=category,
        channel=NotificationChannels.WEBSOCKET,
    )


def should_send_email_notification(
    *,
    preferences,
    dealership,
    recipient,
    notification_type: str,
    category: str,
    priority: str,
    notification: Notification | None = None,
) -> bool:
    if not get_channel_preference(
        preferences=preferences,
        notification_type=notification_type,
        category=category,
        channel=NotificationChannels.EMAIL,
    ):
        return False

    if not is_email_allowed_by_importance(
        preferences=preferences,
        priority=priority,
    ):
        return False

    if not is_email_feature_allowed(
        dealership=dealership,
        recipient=recipient,
        notification=notification,
    ):
        return False

    return True