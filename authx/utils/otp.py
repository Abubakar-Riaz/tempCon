# authx/utils/otp.py

from __future__ import annotations

import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from authx.models import OTPChallenge, OTPPurpose
from core.email import send_email


OTP_TTL_MINUTES = getattr(settings, "OTP_TTL_MINUTES", 10)
OTP_LEN = getattr(settings, "OTP_LENGTH", 6)
MAX_ATTEMPTS = getattr(settings, "OTP_MAX_ATTEMPTS", 5)
MAX_RESENDS = getattr(settings, "OTP_MAX_RESENDS", 5)
RESEND_COOLDOWN_SECONDS = getattr(settings, "OTP_RESEND_COOLDOWN", 30)
BRAND_NAME = getattr(settings, "BRAND_NAME", "BuyCon")


def _gen_code() -> str:
    return str(secrets.randbelow(10**OTP_LEN)).zfill(OTP_LEN)


def _ttl_seconds(challenge: OTPChallenge) -> int:
    return max(0, int((challenge.expires_at - timezone.now()).total_seconds()))


def _request_ip(request) -> str | None:
    if not request:
        return None
    return request.META.get("REMOTE_ADDR")


def _request_user_agent(request) -> str:
    if not request:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


def _attach_ttl_method(challenge: OTPChallenge) -> OTPChallenge:
    challenge.ttl_seconds = lambda: _ttl_seconds(challenge)
    return challenge


def _send_otp_email(
    *,
    email: str,
    code: str,
    title: str,
    lead: str,
    subject: str,
):
    send_email(
        to_email=email,
        subject=subject,
        from_name="OTP Service",
        from_email="no-reply@buycon.com",
        template_name="emails/auth/otp.html",
        context={
            "title": title,
            "lead": lead,
            "code": code,
            "ttl_minutes": OTP_TTL_MINUTES,
        },
    )


def _create_challenge(
    *,
    email: str,
    purpose: str,
    user=None,
    request=None,
    device_id: str | None = None,
    metadata: dict | None = None,
) -> tuple[OTPChallenge, str]:
    code = _gen_code()
    now = timezone.now()

    challenge = OTPChallenge.objects.create(
        user=user,
        email=email.strip().lower(),
        purpose=purpose,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=OTP_TTL_MINUTES),
        max_attempts=MAX_ATTEMPTS,
        max_resends=MAX_RESENDS,
        last_sent_at=now,
        resend_available_at=now + timedelta(seconds=RESEND_COOLDOWN_SECONDS),
        device_id=device_id,
        ip_address=_request_ip(request),
        user_agent=json.dumps(metadata or {}) if metadata else _request_user_agent(request),
    )

    return _attach_ttl_method(challenge), code


def _invalidate_pending(
    *,
    user=None,
    email: str,
    purpose: str,
    device_id: str | None = None,
):
    qs = OTPChallenge.objects.filter(
        email=email.strip().lower(),
        purpose=purpose,
        consumed_at__isnull=True,
    )

    if user is not None:
        qs = qs.filter(user=user)

    if device_id is not None:
        qs = qs.filter(device_id=device_id)

    qs.update(consumed_at=timezone.now())


def _verify_common(*, challenge_id: str, purpose: str, code: str) -> OTPChallenge:
    with transaction.atomic():
        challenge = (
            OTPChallenge.objects
            .select_for_update()
            .select_related("user")
            .filter(public_id=challenge_id, purpose=purpose)
            .first()
        )

        if not challenge or challenge.is_consumed:
            raise ValueError("OTP_INVALID")

        if challenge.is_expired():
            raise ValueError("OTP_EXPIRED")

        if challenge.is_locked():
            raise ValueError("OTP_LOCKED")

        if challenge.attempt_count >= challenge.max_attempts:
            challenge.locked_until = timezone.now() + timedelta(minutes=10)
            challenge.save(update_fields=["locked_until"])
            raise ValueError("OTP_MAX_ATTEMPTS")

        challenge.attempt_count += 1

        if not check_password(code, challenge.code_hash):
            challenge.save(update_fields=["attempt_count"])
            raise ValueError("OTP_INVALID")

        challenge.consumed_at = timezone.now()
        challenge.save(update_fields=["attempt_count", "consumed_at"])

    return _attach_ttl_method(challenge)


def _resend_common(
    *,
    challenge_id: str,
    purpose: str,
    title: str,
    lead: str,
    subject: str,
) -> OTPChallenge:
    now = timezone.now()

    with transaction.atomic():
        challenge = (
            OTPChallenge.objects
            .select_for_update()
            .select_related("user")
            .filter(public_id=challenge_id, purpose=purpose)
            .first()
        )

        if not challenge or challenge.is_consumed or challenge.is_expired():
            raise ValueError("OTP_INVALID")

        if not challenge.can_resend():
            raise TimeoutError("RATE_LIMITED")

        code = _gen_code()

        challenge.code_hash = make_password(code)
        challenge.expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
        challenge.resend_count += 1
        challenge.last_sent_at = now
        challenge.resend_available_at = now + timedelta(seconds=RESEND_COOLDOWN_SECONDS)
        challenge.save(
            update_fields=[
                "code_hash",
                "expires_at",
                "resend_count",
                "last_sent_at",
                "resend_available_at",
            ]
        )

    _send_otp_email(
        email=challenge.email,
        code=code,
        title=title,
        lead=lead,
        subject=subject,
    )

    return _attach_ttl_method(challenge)


def create_signup_challenge(
    email: str,
    *,
    company_name: str,
    request=None,
    set_password: str | None = None,
) -> OTPChallenge:
    User = get_user_model()
    email = email.strip().lower()

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "is_active": False,
            "is_email_verified": False,
        },
    )

    if created and set_password:
        user.set_password(set_password)
        user.save(update_fields=["password"])

    _invalidate_pending(
        user=user,
        email=email,
        purpose=OTPPurpose.SIGNUP_VERIFY,
    )

    challenge, code = _create_challenge(
        user=user,
        email=email,
        purpose=OTPPurpose.SIGNUP_VERIFY,
        request=request,
        metadata={"company_name": company_name},
    )

    _send_otp_email(
        email=email,
        code=code,
        title="Verify your email",
        lead=f"Use this code to verify your email for {company_name}.",
        subject=f"Your {BRAND_NAME} signup code",
    )

    return challenge


def verify_signup_challenge(challenge_id: str, code: str) -> OTPChallenge:
    return _verify_common(
        challenge_id=challenge_id,
        purpose=OTPPurpose.SIGNUP_VERIFY,
        code=code,
    )


def resend_signup_challenge(challenge_id: str) -> OTPChallenge:
    return _resend_common(
        challenge_id=challenge_id,
        purpose=OTPPurpose.SIGNUP_VERIFY,
        title="Your signup code",
        lead="Use this code to continue signing up.",
        subject=f"Your {BRAND_NAME} signup code",
    )


def create_login_challenge(
    *,
    user,
    request=None,
    device_id: str | None = None,
) -> OTPChallenge:
    email = user.email.strip().lower()

    _invalidate_pending(
        user=user,
        email=email,
        purpose=OTPPurpose.LOGIN_NEW_DEVICE,
        device_id=device_id,
    )

    challenge, code = _create_challenge(
        user=user,
        email=email,
        purpose=OTPPurpose.LOGIN_NEW_DEVICE,
        request=request,
        device_id=device_id,
    )

    _send_otp_email(
        email=email,
        code=code,
        title="New device verification",
        lead="Use this code to finish signing in on your new device.",
        subject=f"Your {BRAND_NAME} login code",
    )

    return challenge


def verify_login_challenge(challenge_id: str, code: str) -> OTPChallenge:
    return _verify_common(
        challenge_id=challenge_id,
        purpose=OTPPurpose.LOGIN_NEW_DEVICE,
        code=code,
    )


def resend_login_challenge(challenge_id: str) -> OTPChallenge:
    return _resend_common(
        challenge_id=challenge_id,
        purpose=OTPPurpose.LOGIN_NEW_DEVICE,
        title="Your login code",
        lead="Use this code to finish signing in.",
        subject=f"Your {BRAND_NAME} login code",
    )


def create_password_set_challenge(*, user, request=None):
    email = user.email.strip().lower()

    _invalidate_pending(
        user=user,
        email=email,
        purpose=OTPPurpose.PASSWORD_SET,
    )

    challenge, code = _create_challenge(
        user=user,
        email=email,
        purpose=OTPPurpose.PASSWORD_SET,
        request=request,
    )

    _send_otp_email(
        email=email,
        code=code,
        title="Confirm password reset",
        lead="Use this code to finish resetting your password.",
        subject=f"Your {BRAND_NAME} password reset code",
    )

    return challenge


def verify_password_set_challenge(*, challenge_id: str, code: str):
    return _verify_common(
        challenge_id=challenge_id,
        purpose=OTPPurpose.PASSWORD_SET,
        code=code,
    )