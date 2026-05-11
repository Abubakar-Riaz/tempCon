# notifications/channels/push.py

from notifications.models import NotificationDelivery


def send_push_delivery(*, delivery: NotificationDelivery) -> NotificationDelivery:
    delivery.mark_skipped("Push notifications are not implemented yet.")
    return delivery