#core/authz/request_context.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import PermissionDenied
from django.forms import ValidationError

from core.authz.resolver import build_access_context

DEALERSHIP_HEADER = "HTTP_X_DEALERSHIP_ID"


class MissingDealershipHeader(PermissionDenied):
    pass


class InvalidDealership(PermissionDenied):
    pass


class MembershipRequired(PermissionDenied):
    pass


@dataclass
class RequestDealershipContext:
    user: Any
    dealership: Any
    membership: Any
    company: Any
    subscription: Any | None


def get_dealership_public_id_from_request(request) -> str:
    return (request.META.get(DEALERSHIP_HEADER) or "").strip()


def _get_active_membership_queryset(user):
    from accounts.models import DealershipMembership, MembershipStatus

    return (
        DealershipMembership.objects
        .select_related("dealership", "company", "user")
        .filter(
            user=user,
            status=MembershipStatus.ACTIVE,
            dealership__is_active=True,
            company__is_active=True,
        )
        .order_by("-is_default", "created_at")
    )


def resolve_default_dealership_context(request) -> RequestDealershipContext:
    user = getattr(request, "user", None)

    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")

    membership = _get_active_membership_queryset(user).first()

    if not membership:
        raise MembershipRequired("You do not belong to any active dealership.")

    dealership = membership.dealership
    subscription = getattr(dealership.company, "subscription", None)

    return RequestDealershipContext(
        user=user,
        dealership=dealership,
        membership=membership,
        company=dealership.company,
        subscription=subscription,
    )


def resolve_request_dealership_context(request) -> RequestDealershipContext:
    user = getattr(request, "user", None)

    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")

    dealership_public_id = get_dealership_public_id_from_request(request)

    if not dealership_public_id:
        return resolve_default_dealership_context(request)

    from accounts.models import Dealership, DealershipMembership, MembershipStatus

    try:
        dealership = (
            Dealership.objects
            .select_related("company")
            .get(
                public_id=dealership_public_id,
                is_active=True,
                company__is_active=True,
            )
        )
    except Dealership.DoesNotExist as exc:
        raise InvalidDealership("Invalid dealership.") from exc

    try:
        membership = (
            DealershipMembership.objects
            .select_related("dealership", "company", "user")
            .get(
                user=user,
                dealership=dealership,
                status=MembershipStatus.ACTIVE,
            )
        )
    except DealershipMembership.DoesNotExist as exc:
        raise MembershipRequired("You do not have access to this dealership.") from exc

    subscription = getattr(dealership.company, "subscription", None)

    return RequestDealershipContext(
        user=user,
        dealership=dealership,
        membership=membership,
        company=dealership.company,
        subscription=subscription,
    )


def _get_access_context(request):
    raw_ctx = resolve_request_dealership_context(request)

    ctx = build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )

    return raw_ctx, ctx


def _get_company_scoped_dealership_or_404(*, company, dealership_public_id: str):
    from accounts.models import Dealership

    try:
        return Dealership.objects.get(
            public_id=dealership_public_id,
            company=company,
        )
    except Dealership.DoesNotExist as exc:
        raise ValidationError({"detail": "Invalid dealership."}) from exc