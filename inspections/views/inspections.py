# inspections/views/inspections.py

from django.db.models import Count
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import Vehicle
from inspections.models import Inspection
from inspections.serializers import InspectionDetailSerializer


class VehicleInspectionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INSPECTIONS):
            return Response(
                {"detail": "You do not have permission to view inspections."},
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

        inspection = (
            Inspection.objects
            .select_related("inspector")
            .filter(vehicle=vehicle)
            .order_by("-started_at", "-id")
            .first()
        )

        if not inspection:
            return Response(
                {"detail": "Inspection not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        inspection.items_with_counts = (
            inspection.items
            .select_related("trade")
            .annotate(attachments_count=Count("item_attachments"))
            .order_by("trade__order_index", "trade_label", "label")
        )

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "inspection": InspectionDetailSerializer(
                    inspection,
                    context={
                        "permissions": {
                            "can_update": has_permission(ctx, Permissions.MANAGE_INSPECTIONS),
                            "can_upload_attachments": has_permission(ctx, Permissions.MANAGE_INSPECTIONS),
                        }
                    },
                ).data,
            }
        )


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )