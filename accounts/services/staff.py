# accounts/services/staff.py

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.models import DealershipMembership, DealershipRole, MembershipStatus
from core.authz.permissions import Permissions
from core.authz.resolver import get_effective_permissions, has_permission


ROLE_PRIORITY = [
    DealershipRole.ADMIN,
    DealershipRole.MANAGER,
    DealershipRole.RECON_MANAGER,
    DealershipRole.INSPECTOR,
    DealershipRole.VENDOR,
]

MANAGER_ALLOWED_ROLES = {
    DealershipRole.RECON_MANAGER,
    DealershipRole.INSPECTOR,
    DealershipRole.VENDOR,
}


def normalize_staff_role(roles: list[str] | str) -> str:
    if isinstance(roles, str):
        roles = [roles]

    roles_set = {str(role).lower() for role in roles if role}

    if DealershipRole.ADMIN in roles_set:
        return DealershipRole.ADMIN

    if DealershipRole.VENDOR in roles_set:
        return DealershipRole.VENDOR

    for role in ROLE_PRIORITY:
        if role in roles_set:
            return role

    raise ValidationError({"role": "Invalid role."})


def serialize_permission_flags(membership: DealershipMembership) -> dict[str, bool]:
    permissions = get_effective_permissions(membership)

    return {
        permission: permission in permissions
        for permission in Permissions.all()
    }


def assert_can_view_staff(ctx):
    if not has_permission(ctx, Permissions.VIEW_STAFF):
        raise PermissionDenied("You do not have permission to view staff.")


def assert_can_manage_staff(ctx, target: DealershipMembership | None = None):
    if not has_permission(ctx, Permissions.MANAGE_STAFF):
        raise PermissionDenied("You do not have permission to manage staff.")

    if target is None:
        return

    if target.id == ctx.membership.id:
        raise PermissionDenied("You cannot manage yourself.")

    if target.is_company_owner:
        raise PermissionDenied("Account owner cannot be managed.")

    actor_role = ctx.membership.role

    if actor_role == DealershipRole.ADMIN:
        return

    if actor_role == DealershipRole.MANAGER:
        if target.role in {DealershipRole.ADMIN, DealershipRole.MANAGER}:
            raise PermissionDenied("Managers can only manage lower roles.")
        return

    raise PermissionDenied("You cannot manage staff.")


def assert_can_assign_role(ctx, role: str):
    actor_role = ctx.membership.role

    if actor_role == DealershipRole.ADMIN:
        return

    if actor_role == DealershipRole.MANAGER and role in MANAGER_ALLOWED_ROLES:
        return

    raise PermissionDenied("You cannot assign this role.")


def get_staff_queryset(*, dealership, search: str = "", role: str = ""):
    qs = (
        DealershipMembership.objects
        .filter(
            dealership=dealership,
            status=MembershipStatus.ACTIVE,
            user__is_active=True,
        )
        .select_related("user", "company", "dealership")
        .order_by("user__full_name", "user__email")
    )

    if search:
        qs = qs.filter(
            user__email__icontains=search
        ) | qs.filter(
            user__full_name__icontains=search
        ) | qs.filter(
            user__first_name__icontains=search
        ) | qs.filter(
            user__last_name__icontains=search
        )

    if role:
        qs = qs.filter(role=role)

    return qs.distinct()


def get_staff_member_or_404(*, dealership, member_public_id: str):
    return (
        DealershipMembership.objects
        .select_related("user", "company", "dealership")
        .get(
            public_id=member_public_id,
            dealership=dealership,
            status=MembershipStatus.ACTIVE,
        )
    )


@transaction.atomic
def change_staff_role(*, ctx, target: DealershipMembership, roles: list[str] | str):
    assert_can_manage_staff(ctx, target)

    role = normalize_staff_role(roles)
    assert_can_assign_role(ctx, role)

    target.role = role
    target.save(update_fields=["role", "updated_at"])

    return target


@transaction.atomic
def update_staff_permissions(
    *,
    ctx,
    target: DealershipMembership,
    allow: list[str] | None = None,
    deny: list[str] | None = None,
):
    assert_can_manage_staff(ctx, target)

    allow_set = set(allow or [])
    deny_set = set(deny or [])

    invalid = (allow_set | deny_set) - Permissions.all()
    if invalid:
        raise ValidationError({"permissions": f"Invalid permissions: {sorted(invalid)}"})

    target.permission_overrides = {
        "allow": sorted(allow_set),
        "deny": sorted(deny_set),
    }
    target.save(update_fields=["permission_overrides", "updated_at"])

    return target


@transaction.atomic
def remove_staff_member(*, ctx, target: DealershipMembership):
    assert_can_manage_staff(ctx, target)

    target.status = MembershipStatus.REMOVED
    target.is_default = False
    target.save(update_fields=["status", "is_default", "updated_at"])

    return target