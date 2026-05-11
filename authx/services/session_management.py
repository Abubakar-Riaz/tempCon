# authx/services/session_management.py

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from authx.models import UserSession


def revoke_session(user, session_public_id: str):
    session = (
        UserSession.objects
        .filter(
            user=user,
            public_id=session_public_id,
            revoked_at__isnull=True,
        )
        .first()
    )

    if not session:
        raise ValidationError("Session not found.")

    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])

    return session


def revoke_all_sessions(user, *, except_device_id: str | None = None):
    qs = UserSession.objects.filter(
        user=user,
        revoked_at__isnull=True,
    )

    if except_device_id:
        qs = qs.exclude(device_id=except_device_id)

    return qs.update(revoked_at=timezone.now())