# notifications/views.py

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission
from notifications.pagination import NotificationPagination
from notifications.selectors import (
    get_or_create_notification_preference,
    get_unread_notification_count,
    get_user_notification_or_none,
    get_user_notifications_queryset,
)
from notifications.serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_NOTIFICATIONS):
            return Response({"detail": "You do not have permission to view notifications."}, status=403)

        queryset = get_user_notifications_queryset(
            user=request.user,
            dealership=ctx.dealership,
        )

        is_read = request.query_params.get("is_read")
        category = (request.query_params.get("category") or "").strip()
        notification_type = (request.query_params.get("type") or "").strip()
        priority = (request.query_params.get("priority") or "").strip()

        if is_read in {"true", "1", "yes"}:
            queryset = queryset.filter(is_read=True)
        elif is_read in {"false", "0", "no"}:
            queryset = queryset.filter(is_read=False)

        if category:
            queryset = queryset.filter(category=category)

        if notification_type:
            queryset = queryset.filter(type=notification_type)

        if priority:
            queryset = queryset.filter(priority=priority)

        paginator = NotificationPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        return paginator.get_paginated_response(
            NotificationSerializer(page, many=True).data
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ctx = _get_ctx(request)

        return Response(
            {
                "unread_count": get_unread_notification_count(
                    user=request.user,
                    dealership=ctx.dealership,
                )
            }
        )


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id: str):
        ctx = _get_ctx(request)
        notification = get_user_notification_or_none(
            user=request.user,
            dealership=ctx.dealership,
            notification_public_id=notification_id,
        )

        if notification is None:
            raise NotFound("Notification not found.")

        notification.mark_read()

        return Response(
            {
                "notification": NotificationSerializer(notification).data,
                "unread_count": get_unread_notification_count(
                    user=request.user,
                    dealership=ctx.dealership,
                ),
            }
        )


class NotificationMarkUnreadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id: str):
        ctx = _get_ctx(request)
        notification = get_user_notification_or_none(
            user=request.user,
            dealership=ctx.dealership,
            notification_public_id=notification_id,
        )

        if notification is None:
            raise NotFound("Notification not found.")

        notification.mark_unread()

        return Response(
            {
                "notification": NotificationSerializer(notification).data,
                "unread_count": get_unread_notification_count(
                    user=request.user,
                    dealership=ctx.dealership,
                ),
            }
        )


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        ctx = _get_ctx(request)
        now = timezone.now()

        updated_count = (
            get_user_notifications_queryset(user=request.user, dealership=ctx.dealership)
            .filter(is_read=False)
            .update(is_read=True, read_at=now, updated_at=now)
        )

        return Response(
            {
                "updated_count": updated_count,
                "unread_count": 0,
            }
        )


class NotificationPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ctx = _get_ctx(request)
        preference = get_or_create_notification_preference(
            user=request.user,
            dealership=ctx.dealership,
        )

        return Response(
            {
                "preferences": NotificationPreferenceSerializer(preference).data,
            }
        )

    def patch(self, request):
        ctx = _get_ctx(request)
        preference = get_or_create_notification_preference(
            user=request.user,
            dealership=ctx.dealership,
        )

        serializer = NotificationPreferenceSerializer(
            preference,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"preferences": serializer.data})


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)
    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )