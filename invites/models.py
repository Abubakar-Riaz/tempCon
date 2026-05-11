# invites/models.py

from __future__ import annotations

import secrets

from django.db import models
from django.utils import timezone

from accounts.models import Company, Dealership, DealershipMembership, DealershipRole, User
from core.models.base import PublicIDModel, TimestampedModel


class InviteStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    REVOKED = "revoked", "Revoked"
    EXPIRED = "expired", "Expired"


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


class DealershipInvite(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="dealership_invites",
    )

    dealership = models.ForeignKey(
        Dealership,
        on_delete=models.CASCADE,
        related_name="invites",
    )

    email = models.EmailField(db_index=True)

    role = models.CharField(
        max_length=20,
        choices=DealershipRole.choices,
        default=DealershipRole.VENDOR,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=InviteStatus.choices,
        default=InviteStatus.PENDING,
        db_index=True,
    )

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_dealership_invites",
    )

    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_dealership_invites",
    )

    membership = models.ForeignKey(
        DealershipMembership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_invites",
    )

    token = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        blank=True,
    )

    expires_at = models.DateTimeField(null=True, blank=True)

    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "invites_dealership_invite"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["dealership", "status"]),
            models.Index(fields=["dealership", "email"]),
            models.Index(fields=["email", "status"]),
            models.Index(fields=["token"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["dealership", "email"],
                condition=models.Q(status=InviteStatus.PENDING),
                name="uniq_pending_invite_per_dealership_email",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.email} -> {self.dealership.name} ({self.role}) [{self.status}]"

    def save(self, *args, **kwargs):
        if self.dealership_id:
            self.company_id = self.dealership.company_id

        if not self.token:
            self.token = generate_invite_token()

        super().save(*args, **kwargs)

    @property
    def is_pending(self) -> bool:
        return self.status == InviteStatus.PENDING

    @property
    def is_accepted(self) -> bool:
        return self.status == InviteStatus.ACCEPTED

    @property
    def is_revoked(self) -> bool:
        return self.status == InviteStatus.REVOKED

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    @property
    def can_be_accepted(self) -> bool:
        return self.status == InviteStatus.PENDING and not self.is_expired

    def mark_accepted(
        self,
        *,
        user: User | None = None,
        membership: DealershipMembership | None = None,
    ):
        self.status = InviteStatus.ACCEPTED
        self.accepted_at = timezone.now()
        self.accepted_by = user

        if membership is not None:
            self.membership = membership

    def mark_revoked(self):
        self.status = InviteStatus.REVOKED
        self.revoked_at = timezone.now()

    def mark_expired(self):
        self.status = InviteStatus.EXPIRED