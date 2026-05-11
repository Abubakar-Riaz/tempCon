# notifications/urls.py

from django.urls import path

from notifications.views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationMarkUnreadView,
    NotificationPreferenceView,
    NotificationUnreadCountView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("mark-all-read/", NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
    path("preferences/", NotificationPreferenceView.as_view(), name="notification-preferences"),
    path("<uuid:notification_id>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("<uuid:notification_id>/unread/", NotificationMarkUnreadView.as_view(), name="notification-mark-unread"),
]