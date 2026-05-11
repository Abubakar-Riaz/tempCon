# notifications/selectors.py

from notifications.models import Notification, NotificationPreference


def get_user_notifications_queryset(*, user, dealership):
    return (
        Notification.objects
        .filter(
            recipient=user,
            dealership=dealership,
        )
        .select_related("recipient", "actor", "dealership")
        .order_by("-created_at")
    )


def get_user_notification_or_none(*, user, dealership, notification_public_id: str):
    return (
        get_user_notifications_queryset(user=user, dealership=dealership)
        .filter(public_id=notification_public_id)
        .first()
    )


def get_unread_notification_count(*, user, dealership) -> int:
    return Notification.objects.filter(
        recipient=user,
        dealership=dealership,
        is_read=False,
    ).count()


def get_or_create_notification_preference(*, user, dealership):
    preference, _ = NotificationPreference.objects.get_or_create(
        user=user,
        dealership=dealership,
    )
    return preference