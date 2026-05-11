# vendors/views/vendors.py

from __future__ import annotations

from django.db.models import Q
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import DealershipMembership, MembershipStatus
from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import (
    build_access_context,
    get_membership_permissions,
    has_permission,
)
from vendors.serializers import DealershipVendorSerializer


class VendorsPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class DealershipVendorsListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = VendorsPagination

    def get(self, request):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_RECON):
            return Response(
                {"detail": "You do not have permission to view vendors."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            DealershipMembership.objects
            .select_related("user", "dealership", "company")
            .filter(
                dealership=ctx.dealership,
                status=MembershipStatus.ACTIVE,
            )
            .order_by("user__email")
        )

        vendor_ids = [
            membership.id
            for membership in qs
            if Permissions.MANAGE_VENDOR_WORK in get_membership_permissions(membership)
        ]

        qs = qs.filter(id__in=vendor_ids)

        search = (request.query_params.get("q") or "").strip()
        if search:
            qs = qs.filter(
                Q(user__email__icontains=search)
                | Q(user__full_name__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        return paginator.get_paginated_response(
            DealershipVendorSerializer(page, many=True).data
        )


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )