# authx/models.py

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.models.base import PublicIDModel, TimestampedModel


User = get_user_model()


class AuthProvider(models.TextChoices):
    PASSWORD = "password", "Password"
    GOOGLE = "google", "Google"


class OTPPurpose(models.TextChoices):
    SIGNUP_VERIFY = "signup_verify", "Signup Verify"
    LOGIN_NEW_DEVICE = "login_new_device", "Login New Device"
    PASSWORD_SET = "password_set", "Password Set/Reset"


class OTPChallenge(PublicIDModel, models.Model):
    """
    Stores OTP challenges for email verification, new-device login,
    and password set/reset.

    Store only hashed OTP codes.
    Tracks verification attempts and resend cooldowns.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otp_challenges",
        null=True,
        blank=True,
    )

    email = models.EmailField(db_index=True)

    purpose = models.CharField(
        max_length=32,
        choices=OTPPurpose.choices,
        db_index=True,
    )

    code_hash = models.CharField(max_length=128)

    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    locked_until = models.DateTimeField(null=True, blank=True)

    resend_count = models.PositiveSmallIntegerField(default=0)
    max_resends = models.PositiveSmallIntegerField(default=5)
    last_sent_at = models.DateTimeField(null=True, blank=True)
    resend_available_at = models.DateTimeField(null=True, blank=True)

    device_id = models.CharField(max_length=64, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "authx_otp_challenge"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["email", "purpose", "expires_at"]),
            models.Index(fields=["purpose", "consumed_at"]),
            models.Index(fields=["email", "purpose", "resend_available_at"]),
        ]

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def is_locked(self) -> bool:
        return self.locked_until is not None and timezone.now() < self.locked_until

    def can_resend(self) -> bool:
        if self.resend_count >= self.max_resends:
            return False

        if self.resend_available_at is None:
            return True

        return timezone.now() >= self.resend_available_at


class UserProvider(PublicIDModel, TimestampedModel):
    """
    Tracks which providers a user has linked.

    For Google, provider_uid stores the Google `sub`.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="providers",
    )

    provider = models.CharField(
        max_length=24,
        choices=AuthProvider.choices,
        db_index=True,
    )

    provider_uid = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        db_table = "authx_user_provider"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="uniq_user_provider",
            ),
        ]
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["provider", "provider_uid"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} / {self.provider}"


class LoginStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"


class LoginMethod(models.TextChoices):
    PASSWORD = "password", "Password"
    GOOGLE = "google", "Google"
    OTP = "otp", "OTP"


class LoginEvent(PublicIDModel, models.Model):
    """
    Append-only login/audit history.
    Store IP internally for security.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_events",
    )

    email = models.EmailField(blank=True, default="", db_index=True)

    status = models.CharField(
        max_length=16,
        choices=LoginStatus.choices,
        db_index=True,
    )

    method = models.CharField(
        max_length=24,
        choices=LoginMethod.choices,
        db_index=True,
    )

    device_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )

    device_label = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )

    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    location_label = models.CharField(max_length=128, blank=True, default="")
    failure_reason = models.CharField(max_length=128, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "authx_login_event"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["email", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]


class UserSession(PublicIDModel, models.Model):
    """
    DB record representing a refreshable login session.

    Tied to device_id for new-device OTP and current-devices screens.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sessions",
    )

    device_id = models.CharField(max_length=64, db_index=True)
    device_label = models.CharField(max_length=128, null=True, blank=True)

    user_agent = models.TextField(null=True, blank=True)

    ip_created = models.GenericIPAddressField(null=True, blank=True)
    ip_last = models.GenericIPAddressField(null=True, blank=True)

    location_label = models.CharField(max_length=128, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)

    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    refresh_jti = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        db_table = "authx_user_session"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["user", "device_id", "revoked_at"]),
            models.Index(fields=["user", "last_seen_at"]),
            models.Index(fields=["user", "revoked_at", "last_seen_at"]),
        ]

    def is_active(self) -> bool:
        return self.revoked_at is None