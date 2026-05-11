# accounts/services/dealerships.py

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from accounts.models import Dealership, DealershipMembership, MembershipStatus
from core.authz.features import Features
from core.authz.limits import Limits
from core.authz.permissions import Permissions
from core.authz.resolver import get_limit, has_feature, has_permission


def assert_can_list_dealerships(ctx):
    if has_permission(ctx, Permissions.VIEW_ALL_DEALERSHIPS):
        return

    if has_permission(ctx, Permissions.VIEW_OWN_DEALERSHIPS):
        return

    raise PermissionDenied("You do not have permission to view dealerships.")


def assert_can_create_dealership(ctx):
    if not has_permission(ctx, Permissions.CREATE_DEALERSHIP):
        raise PermissionDenied("You do not have permission to create dealerships.")

    if not has_feature(ctx, Features.MULTI_DEALERSHIP):
        raise PermissionDenied("Multi-dealership is not available on this plan.")

    max_dealerships = get_limit(ctx, Limits.MAX_DEALERSHIPS)

    if max_dealerships is not None:
        current_count = Dealership.objects.filter(
            company=ctx.company,
            is_active=True,
        ).count()

        if current_count >= int(max_dealerships):
            raise PermissionDenied("Dealership limit reached.")


def assert_can_view_dealership(ctx, dealership):
    if dealership.company_id != ctx.company.id:
        raise PermissionDenied("You do not have access to this dealership.")

    if has_permission(ctx, Permissions.VIEW_ALL_DEALERSHIPS):
        return

    if (
        has_permission(ctx, Permissions.VIEW_OWN_DEALERSHIPS)
        and dealership.id == ctx.dealership.id
    ):
        return

    if (
        has_permission(ctx, Permissions.VIEW_DEALERSHIP)
        and dealership.id == ctx.dealership.id
    ):
        return

    raise PermissionDenied("You do not have permission to view this dealership.")


def assert_can_manage_dealership(ctx, dealership):
    if dealership.company_id != ctx.company.id:
        raise PermissionDenied("You do not have access to this dealership.")

    if not has_permission(ctx, Permissions.EDIT_DEALERSHIP):
        raise PermissionDenied("You do not have permission to update dealerships.")


def get_visible_dealerships(ctx):
    assert_can_list_dealerships(ctx)

    qs = Dealership.objects.filter(
        company=ctx.company,
        is_active=True,
    ).order_by("name")

    if has_permission(ctx, Permissions.VIEW_ALL_DEALERSHIPS):
        return qs

    dealership_ids = (
        DealershipMembership.objects
        .filter(
            user=ctx.user,
            company=ctx.company,
            status=MembershipStatus.ACTIVE,
            dealership__is_active=True,
        )
        .values_list("dealership_id", flat=True)
    )

    return qs.filter(id__in=dealership_ids)


def get_dealership_for_company_or_404(*, ctx, dealership_public_id):
    dealership = Dealership.objects.get(
        public_id=dealership_public_id,
        company=ctx.company,
    )

    assert_can_view_dealership(ctx, dealership)

    return dealership


@transaction.atomic
def create_dealership(*, ctx, name: str):
    assert_can_create_dealership(ctx)

    return Dealership.objects.create(
        company=ctx.company,
        name=name.strip(),
        created_by=ctx.user,
    )


@transaction.atomic
def update_dealership(*, ctx, dealership, data: dict):
    assert_can_manage_dealership(ctx, dealership)

    for field, value in data.items():
        setattr(dealership, field, value)

    dealership.save()

    return dealership