# inventory/views/vehicle_history.py

from __future__ import annotations

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import HistoryEvent, Vehicle
from inventory.serializers.vehicles import VehicleHistoryEventSerializer


class VehicleHistoryPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )


class VehicleHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = VehicleHistoryPagination

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INVENTORY):
            return Response(
                {"detail": "You do not have permission to view vehicle history."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = Vehicle.objects.filter(
            company=ctx.company,
            dealership=ctx.dealership,
            public_id=vehicle_id,
        ).first()

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = (
            HistoryEvent.objects
            .select_related("actor")
            .filter(vehicle=vehicle)
            .order_by("-occurred_at", "-created_at")
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        return paginator.get_paginated_response(
            VehicleHistoryEventSerializer(page, many=True).data
        )