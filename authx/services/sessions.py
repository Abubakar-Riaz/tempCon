# authx/services/sessions.py

from __future__ import annotations

import secrets

from django.conf import settings
from django.utils import timezone

from authx.models import UserSession
from authx.utils.tokens import issue_tokens


DEVICE_COOKIE_NAME = getattr(settings, "AUTH_DEVICE_COOKIE_NAME", "bc_device_id")


def ensure_device_id(request) -> tuple[str, bool]:
    device_id = (request.COOKIES.get(DEVICE_COOKIE_NAME) or "").strip()

    if device_id:
        return device_id, False

    return secrets.token_urlsafe(32), True


def set_device_cookie(response, device_id: str):
    response.set_cookie(
        DEVICE_COOKIE_NAME,
        device_id,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )


def is_known_device(user, device_id: str) -> bool:
    return UserSession.objects.filter(
        user=user,
        device_id=device_id,
        revoked_at__isnull=True,
    ).exists()


def issue_tokens_and_session(*, user, request, device_id: str):
    access, refresh = issue_tokens(user)

    session, _ = UserSession.objects.update_or_create(
        user=user,
        device_id=device_id,
        revoked_at__isnull=True,
        defaults={
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "ip_last": request.META.get("REMOTE_ADDR"),
            "last_seen_at": timezone.now(),
        },
    )

    if not session.ip_created:
        session.ip_created = request.META.get("REMOTE_ADDR")
        session.save(update_fields=["ip_created"])

    return access, refresh, session