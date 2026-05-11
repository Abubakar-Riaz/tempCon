# invites/services.py

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import DealershipMembership, DealershipRole, MembershipStatus
from core.authz.features import Features
from core.authz.limits import Limits
from core.authz.permissions import Permissions
from core.authz.resolver import get_limit, has_feature, has_permission
from core.email import send_email
from invites.models import DealershipInvite, InviteStatus, generate_invite_token

User = get_user_model()


def _invite_accept_url(invite: DealershipInvite) -> str:
    frontend_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    path = f"/invite/accept?token={invite.token}"
    return f"{frontend_url}{path}" if frontend_url else path


def send_invite_email(invite: DealershipInvite):
    send_email(
        to_email=invite.email,
        from_email="invites@buycon.com",
        from_name="BuyCon Invitations",
        subject=f"You’ve been invited to {invite.company.name}",
        template_name="emails/invites/dealership_invite.html",
        context={
            "invite": invite,
            "company": invite.company,
            "dealership": invite.dealership,
            "role": invite.role,
            "accept_url": _invite_accept_url(invite),
            "expires_at": invite.expires_at,
        },
    )


def normalize_invite_role(*, ctx, roles: list[str]) -> str:
    roles = list(dict.fromkeys(roles))

    if DealershipRole.VENDOR in roles:
        if len(roles) > 1:
            raise ValidationError({"roles": "Vendor invite cannot include other roles."})
        return DealershipRole.VENDOR

    if DealershipRole.ADMIN in roles:
        if not ctx.membership.is_company_owner:
            raise PermissionDenied("Only account owner can invite admins.")
        if len(roles) > 1:
            raise ValidationError({"roles": "Admin invite cannot include other roles."})
        return DealershipRole.ADMIN

    if DealershipRole.MANAGER in roles:
        return DealershipRole.MANAGER

    if DealershipRole.RECON_MANAGER in roles:
        return DealershipRole.RECON_MANAGER

    if DealershipRole.INSPECTOR in roles:
        return DealershipRole.INSPECTOR
    if DealershipRole.BUYER in roles:
        return DealershipRole.BUYER

    raise ValidationError({"roles": "Invalid invite role."})


def assert_can_invite_role(ctx, role: str):
    if role == DealershipRole.VENDOR:
        if not has_permission(ctx, Permissions.INVITE_VENDORS):
            raise PermissionDenied("You do not have permission to invite vendors.")

        if not has_feature(ctx, Features.VENDOR_INVITES):
            raise PermissionDenied("Vendor invites are not available on this plan.")

        max_vendors = get_limit(ctx, Limits.MAX_VENDOR_USERS)

        if max_vendors is not None:
            used = (
                DealershipMembership.objects
                .filter(
                    company=ctx.company,
                    role=DealershipRole.VENDOR,
                    status=MembershipStatus.ACTIVE,
                )
                .count()
            )

            pending = (
                DealershipInvite.objects
                .filter(
                    company=ctx.company,
                    role=DealershipRole.VENDOR,
                    status=InviteStatus.PENDING,
                )
                .count()
            )

            if used + pending >= int(max_vendors):
                raise PermissionDenied("Vendor invite limit reached.")

        return

    if not has_permission(ctx, Permissions.INVITE_STAFF) and not has_permission(ctx, Permissions.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to invite staff.")

    if not has_feature(ctx, Features.STAFF_INVITES):
        raise PermissionDenied("Staff invites are not available on this plan.")

    max_users = get_limit(ctx, Limits.MAX_USERS)

    if max_users is not None:
        used = (
            DealershipMembership.objects
            .filter(
                company=ctx.company,
                status=MembershipStatus.ACTIVE,
            )
            .values("user_id")
            .distinct()
            .count()
        )

        pending = (
            DealershipInvite.objects
            .filter(
                company=ctx.company,
                status=InviteStatus.PENDING,
            )
            .exclude(role=DealershipRole.VENDOR)
            .values("email")
            .distinct()
            .count()
        )

        if used + pending >= int(max_users):
            raise PermissionDenied("Staff invite limit reached.")


def assert_can_manage_invite(ctx, invite: DealershipInvite):
    if invite.company_id != ctx.company.id:
        raise PermissionDenied("You do not have access to this invite.")

    if not has_permission(ctx, Permissions.MANAGE_INVITES) and not has_permission(ctx, Permissions.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage invites.")


def get_invites_queryset(ctx):
    if not has_permission(ctx, Permissions.VIEW_INVITES) and not has_permission(ctx, Permissions.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to view invites.")

    return (
        DealershipInvite.objects
        .filter(company=ctx.company)
        .select_related("dealership", "invited_by", "accepted_by", "membership")
        .order_by("-created_at")
    )


def get_invite_or_404(*, ctx, invite_public_id):
    return (
        DealershipInvite.objects
        .select_related("company", "dealership", "invited_by", "accepted_by", "membership")
        .get(public_id=invite_public_id, company=ctx.company)
    )


@transaction.atomic
def create_invite(*, ctx, email: str, roles: list[str]):
    role = normalize_invite_role(ctx=ctx, roles=roles)
    assert_can_invite_role(ctx, role)

    email = email.strip().lower()

    existing_membership = DealershipMembership.objects.filter(
        user__email__iexact=email,
        dealership=ctx.dealership,
        status=MembershipStatus.ACTIVE,
    ).first()

    if existing_membership:
        raise ValidationError({"email": "User is already a member of this dealership."})

    invite, created = DealershipInvite.objects.get_or_create(
        dealership=ctx.dealership,
        email=email,
        status=InviteStatus.PENDING,
        defaults={
            "company": ctx.company,
            "role": role,
            "invited_by": ctx.user,
            "expires_at": timezone.now() + timedelta(days=int(getattr(settings, "INVITE_TTL_DAYS", 14))),
        },
    )

    if not created:
        raise ValidationError({"email": "Pending invite already exists for this dealership."})

    send_invite_email(invite)

    return invite


@transaction.atomic
def resend_invite(*, ctx, invite: DealershipInvite):
    assert_can_manage_invite(ctx, invite)

    if invite.status != InviteStatus.PENDING:
        raise ValidationError({"invite": "Only pending invites can be resent."})

    invite.token = generate_invite_token()
    invite.expires_at = timezone.now() + timedelta(days=int(getattr(settings, "INVITE_TTL_DAYS", 14)))
    invite.save(update_fields=["token", "expires_at", "updated_at"])

    send_invite_email(invite)

    return invite


@transaction.atomic
def revoke_invite(*, ctx, invite: DealershipInvite):
    assert_can_manage_invite(ctx, invite)

    if invite.status != InviteStatus.PENDING:
        raise ValidationError({"invite": "Only pending invites can be revoked."})

    invite.mark_revoked()
    invite.save(update_fields=["status", "revoked_at", "updated_at"])

    return invite


@transaction.atomic
def accept_invite(*, token: str, password: str = ""):
    invite = (
        DealershipInvite.objects
        .select_related("company", "dealership")
        .get(token=token)
    )

    if not invite.can_be_accepted:
        if invite.is_expired and invite.status == InviteStatus.PENDING:
            invite.mark_expired()
            invite.save(update_fields=["status", "updated_at"])
        raise ValidationError({"invite": "Invite cannot be accepted."})

    user = User.objects.filter(email__iexact=invite.email, is_active=True).first()
    created_user = False

    if user is None:
        user = User.objects.create_user(email=invite.email, is_active=True)
        created_user = True

    if password:
        user.set_password(password)
        user.save(update_fields=["password"])

    membership, _ = DealershipMembership.objects.get_or_create(
        user=user,
        dealership=invite.dealership,
        defaults={
            "company": invite.company,
            "role": invite.role,
            "status": MembershipStatus.ACTIVE,
            "invited_by": invite.invited_by,
        },
    )

    if membership.status != MembershipStatus.ACTIVE:
        membership.status = MembershipStatus.ACTIVE

    membership.role = invite.role
    membership.company = invite.company
    membership.save(update_fields=["company", "role", "status", "joined_at", "updated_at"])

    invite.mark_accepted(user=user, membership=membership)
    invite.save(update_fields=["status", "accepted_at", "accepted_by", "membership", "updated_at"])

    return invite, membership, created_user