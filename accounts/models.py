from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone as django_timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from core.models.base import PublicIDModel, TimestampedModel


def user_avatar_upload_to(instance, filename: str) -> str:
    ident = instance.public_id or "unknown"
    return f"avatars/{ident}/avatar/{filename}"


class HourFormat(models.TextChoices):
    H12 = "12", _("12-hour")
    H24 = "24", _("24-hour")


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, PublicIDModel):
    email = models.EmailField(unique=True, db_index=True)

    full_name = models.CharField(max_length=200, blank=True, default="")
    is_email_verified = models.BooleanField(default=False)

    first_name = models.CharField(max_length=100, blank=True, default="")
    last_name = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")

    avatar = models.ImageField(
        upload_to=user_avatar_upload_to,
        blank=True,
        null=True,
    )

    timezone = models.CharField(max_length=64, blank=True, default="")
    language = models.CharField(max_length=16, blank=True, default="en")
    date_format = models.CharField(max_length=32, blank=True, default="MMM D, YYYY")
    hour_format = models.CharField(
        max_length=2,
        choices=HourFormat.choices,
        default=HourFormat.H12,
    )
    week_start = models.CharField(max_length=16, blank=True, default="sunday")

    job_title = models.CharField(max_length=200, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=django_timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["public_id"]),
        ]

    def __str__(self):
        return self.email

    @property
    def display_name(self) -> str:
        if self.full_name:
            return self.full_name.strip()

        combined = f"{self.first_name} {self.last_name}".strip()
        return combined or self.email

    def save(self, *args, **kwargs):
        if not self.full_name:
            combined = f"{self.first_name} {self.last_name}".strip()
            if combined:
                self.full_name = combined

        super().save(*args, **kwargs)


class Company(PublicIDModel, TimestampedModel):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=255, blank=True, default="")
    slug = models.SlugField(max_length=220, unique=True, db_index=True, blank=True)

    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")

    address_line_1 = models.CharField(max_length=255, blank=True, default="")
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=30, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_companies",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["name"]),
            models.Index(fields=["legal_name"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return self.name

    @staticmethod
    def _base_slug(name: str) -> str:
        return slugify(name)[:220] or f"company-{secrets.token_hex(4)}"

    @classmethod
    def generate_unique_slug(cls, name: str, max_attempts: int = 50) -> str:
        base = cls._base_slug(name)

        if not cls.objects.filter(slug=base).exists():
            return base

        for i in range(2, max_attempts + 2):
            candidate = f"{base}-{i}"[:220]
            if not cls.objects.filter(slug=candidate).exists():
                return candidate

        while True:
            candidate = f"{base[:210]}-{secrets.token_hex(4)}"
            if not cls.objects.filter(slug=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug(self.name)

        super().save(*args, **kwargs)


class Dealership(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="dealerships",
    )

    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=255, blank=True, default="")
    slug = models.SlugField(max_length=220, db_index=True, blank=True)

    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=50, blank=True, default="")

    address_line_1 = models.CharField(max_length=255, blank=True, default="")
    address_line_2 = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=100, blank=True, default="")
    postal_code = models.CharField(max_length=30, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_dealerships",
    )

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "is_default"]),
            models.Index(fields=["company", "is_pinned"]),
            models.Index(fields=["company", "slug"]),
            models.Index(fields=["company", "name"]),
            models.Index(fields=["public_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "slug"],
                name="uniq_dealership_slug_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_dealership_name_per_company",
            ),
        ]

    def __str__(self):
        return f"{self.company.name} / {self.name}"

    @staticmethod
    def _base_slug(name: str) -> str:
        return slugify(name)[:220] or f"dealership-{secrets.token_hex(4)}"

    def generate_unique_slug(self, max_attempts: int = 50) -> str:
        base = self._base_slug(self.name)

        if not Dealership.objects.filter(company=self.company, slug=base).exists():
            return base

        for i in range(2, max_attempts + 2):
            candidate = f"{base}-{i}"[:220]
            if not Dealership.objects.filter(company=self.company, slug=candidate).exists():
                return candidate

        while True:
            candidate = f"{base[:210]}-{secrets.token_hex(4)}"
            if not Dealership.objects.filter(company=self.company, slug=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

        if self.is_default:
            type(self).objects.filter(company=self.company).exclude(pk=self.pk).update(
                is_default=False
            )


class MembershipStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INVITED = "invited", _("Invited")
    SUSPENDED = "suspended", _("Suspended")
    REMOVED = "removed", _("Removed")


class DealershipRole(models.TextChoices):
    ADMIN = "admin", _("Admin")
    MANAGER = "manager", _("Manager")
    RECON_MANAGER = "recon_manager", _("Recon Manager")
    BUYER = "buyer", _("Buyer")
    INSPECTOR = "inspector", _("Inspector")
    VENDOR = "vendor", _("Vendor")


class DealershipMembership(PublicIDModel, TimestampedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="dealership_memberships",
    )

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        related_name="memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=DealershipRole.choices,
        default=DealershipRole.VENDOR,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
    )

    is_company_owner = models.BooleanField(default=False, db_index=True)
    is_default = models.BooleanField(default=False)

    permission_overrides = models.JSONField(default=dict, blank=True)

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_dealership_memberships",
    )

    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["dealership", "status"]),
            models.Index(fields=["dealership", "role", "status"]),
            models.Index(fields=["user", "dealership"]),
            models.Index(fields=["public_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "dealership"],
                name="uniq_user_membership_per_dealership",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.dealership.name} ({self.role})"

    def clean(self):
        if self.dealership_id and self.company_id:
            if self.dealership.company_id != self.company_id:
                from django.core.exceptions import ValidationError

                raise ValidationError("Membership company must match dealership.company")

    def save(self, *args, **kwargs):
        if self.dealership_id:
            self.company_id = self.dealership.company_id

        if self.status == MembershipStatus.ACTIVE and self.joined_at is None:
            self.joined_at = django_timezone.now()

        super().save(*args, **kwargs)

        if self.is_default:
            type(self).objects.filter(
                user=self.user,
                company=self.company,
            ).exclude(pk=self.pk).update(is_default=False)

    @property
    def is_admin_like(self):
        return self.role == DealershipRole.ADMIN or self.is_company_owner

    @property
    def can_manage_billing(self):
        return self.is_company_owner


class TrustedDevice(models.Model):
    """
    Stores a one-way hash of a long-lived device token so we can recognize
    trusted browsers and skip OTP the next time the user logs in.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trusted_devices",
    )
    token_hash = models.CharField(max_length=64, db_index=True)
    ip = models.CharField(max_length=45, blank=True, default="")
    user_agent = models.TextField(blank=True, default="")
    last_used = models.DateTimeField(default=django_timezone.now)

    class Meta:
        unique_together = [("user", "token_hash")]
        indexes = [
            models.Index(fields=["user", "token_hash"]),
        ]
        ordering = ["-last_used"]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.token_hash[:8]}"