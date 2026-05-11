# authx/services/passwords.py

from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone

from authx.models import AuthProvider, OTPPurpose, UserProvider, UserSession
from authx.utils.otp import create_password_set_challenge, verify_password_set_challenge
from core.email import send_email

User = get_user_model()

PASSWORD_RESET_SALT = "authx.password-reset"
PASSWORD_RESET_MAX_AGE = 60 * 30


def make_password_reset_token(email: str) -> str:
    return signing.dumps({"email": email.strip().lower()}, salt=PASSWORD_RESET_SALT)


def parse_password_reset_token(token: str) -> str:
    try:
        data = signing.loads(token, salt=PASSWORD_RESET_SALT, max_age=PASSWORD_RESET_MAX_AGE)
    except signing.BadSignature as exc:
        raise ValueError("Invalid or expired reset token.") from exc

    email = (data.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Invalid reset token.")
    return email


def ensure_password_provider(user):
    return UserProvider.objects.get_or_create(user=user, provider=AuthProvider.PASSWORD)


def revoke_all_sessions(user):
    UserSession.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now()
    )


def send_password_reset_email(*, request, user):
    token = make_password_reset_token(user.email)
    reset_url = request.build_absolute_uri(f"/auth/reset-password?token={token}")

    send_email(
        to_email=user.email,
        from_name="BuyCon Support",
        from_email="support@buycon.com",
        subject="Reset your password",
        template_name="emails/auth/password_reset.html",
        context={"reset_url": reset_url, "user": user},
    )


def start_password_reset_otp(*, token: str, request=None):
    email = parse_password_reset_token(token)
    user = User.objects.get(email__iexact=email, is_active=True)

    return create_password_set_challenge(
        user=user,
        request=request,
    )


@transaction.atomic
def confirm_password_reset(*, token: str, otp_challenge_id, otp_code: str, new_password: str):
    email = parse_password_reset_token(token)

    try:
        user = User.objects.get(email__iexact=email, is_active=True)
    except User.DoesNotExist as exc:
        raise ValueError("Invalid reset token.") from exc

    challenge = verify_password_set_challenge(
        challenge_id=otp_challenge_id,
        code=otp_code,
    )

    if challenge.user_id != user.id:
        raise ValueError("Invalid OTP challenge.")

    user.set_password(new_password)
    user.save(update_fields=["password"])

    ensure_password_provider(user)
    revoke_all_sessions(user)

    return user