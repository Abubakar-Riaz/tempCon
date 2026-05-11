from __future__ import annotations

from authx.models import LoginEvent, LoginMethod, LoginStatus


def log_login_event(
    *,
    user,
    email: str,
    status: LoginStatus | str,
    method: LoginMethod | str,
    request,
    device_id: str = "",
    failure_reason: str = "",
):
    return LoginEvent.objects.create(
        user=user,
        email=email or "",
        status=status,
        method=method,
        device_id=device_id or "",
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
        ip_address=request.META.get("REMOTE_ADDR"),
        failure_reason=failure_reason or "",
    )