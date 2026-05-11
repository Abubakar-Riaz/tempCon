# notifications/channels/in_app.py

from notifications.models import NotificationDelivery


def send_in_app_delivery(*, delivery: NotificationDelivery) -> NotificationDelivery:
    delivery.mark_sent()
    return delivery