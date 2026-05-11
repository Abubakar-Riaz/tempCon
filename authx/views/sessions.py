# authx/views/sessions.py

from __future__ import annotations

from django.contrib.auth import logout as django_logout
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authx.models import LoginEvent, UserSession
from authx.parsing_utils import parse_user_agent_summary
from authx.serializers.sessions import (
    ActiveSessionSerializer,
    LoginHistorySerializer,
    SessionRevokeSerializer,
)
from authx.services.session_management import revoke_all_sessions, revoke_session
from authx.services.sessions import DEVICE_COOKIE_NAME
from authx.utils.tokens import (
    blacklist_refresh_token_safely,
    clear_auth_cookies,
    get_refresh_from_request,
)


class SessionListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        current_device_id = (
            request.COOKIES.get(DEVICE_COOKIE_NAME)
            or request.headers.get("X-Device-Id")
        )

        qs = (
            UserSession.objects
            .filter(
                user=request.user,
                revoked_at__isnull=True,
            )
            .order_by("-last_seen_at")
        )

        payload = []

        for session in qs:
            inferred_device, inferred_browser = parse_user_agent_summary(
                session.user_agent or ""
            )

            last_seen = timezone.localtime(session.last_seen_at)

            payload.append(
                {
                    "id": str(session.public_id),
                    "device": (session.device_label or "").strip() or inferred_device or "Unknown",
                    "browser": inferred_browser or "Unknown",
                    "location": (session.location_label or "").strip() or "Unknown",
                    "ip": session.ip_last,
                    "last_active_date": last_seen.date(),
                    "last_active_time": last_seen.time(),
                    "is_current": bool(
                        current_device_id and session.device_id == current_device_id
                    ),
                }
            )

        serializer = ActiveSessionSerializer(payload, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SessionRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        revoke_session(
            request.user,
            str(serializer.validated_data["session_id"]),
        )

        return Response(
            {"detail": "Session revoked."},
            status=status.HTTP_200_OK,
        )


class SessionRevokeAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_device_id = (
            request.COOKIES.get(DEVICE_COOKIE_NAME)
            or request.headers.get("X-Device-Id")
        )

        revoke_all_sessions(
            request.user,
            except_device_id=current_device_id,
        )

        return Response(
            {"detail": "All other sessions revoked."},
            status=status.HTTP_200_OK,
        )


class LoginHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            limit = 10

        limit = max(1, min(limit, 50))

        qs = LoginEvent.objects.filter(user=request.user)

        status_filter = (request.query_params.get("status") or "").strip()
        method_filter = (request.query_params.get("method") or "").strip()
        since_raw = (request.query_params.get("since") or "").strip()
        until_raw = (request.query_params.get("until") or "").strip()

        if status_filter:
            qs = qs.filter(status=status_filter)

        if method_filter:
            qs = qs.filter(method=method_filter)

        if since_raw:
            since = parse_datetime(since_raw)
            if since:
                qs = qs.filter(created_at__gte=since)

        if until_raw:
            until = parse_datetime(until_raw)
            if until:
                qs = qs.filter(created_at__lte=until)

        qs = qs.order_by("-created_at")[:limit]

        payload = []

        for event in qs:
            inferred_device, inferred_browser = parse_user_agent_summary(
                event.user_agent or ""
            )

            created_at = timezone.localtime(event.created_at)

            payload.append(
                {
                    "id": str(event.public_id),
                    "date": created_at.date(),
                    "time": created_at.time(),
                    "device": (event.device_label or "").strip() or inferred_device or "Unknown",
                    "browser": inferred_browser or "Unknown",
                    "location": (event.location_label or "").strip() or "Unknown",
                    "status": event.status,
                    "method": event.method,
                }
            )

        serializer = LoginHistorySerializer(payload, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current_device_id = (
            request.COOKIES.get(DEVICE_COOKIE_NAME)
            or request.headers.get("X-Device-Id")
        )

        refresh_token = get_refresh_from_request(request)

        if refresh_token:
            blacklist_refresh_token_safely(refresh_token)

        if current_device_id:
            UserSession.objects.filter(
                user=request.user,
                device_id=current_device_id,
                revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())

        django_logout(request._request)

        response = Response(
            {"detail": "Logged out."},
            status=status.HTTP_200_OK,
        )
        clear_auth_cookies(response)

        return response