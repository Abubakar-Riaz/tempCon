# inventory/views/vehicle_phase.py

from __future__ import annotations

from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import Vehicle
from inventory.serializers.phase import VehiclePhaseAdvanceSerializer
from inventory.serializers.vehicles import VehicleDetailSerializer
from inventory.services.vehicle_phases import (
    ASSIGNEE_PERMISSION_FOR_PHASE,
    advance_vehicle_phase,
    can_advance_vehicle,
    get_assignable_membership,
    get_next_phase,
)


class VehiclePhaseAdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INVENTORY):
            return Response(
                {"detail": "You do not have permission to access inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = (
            Vehicle.objects
            .select_for_update()
            .select_related("dealership", "created_by", "updated_by")
            .filter(
                company=ctx.company,
                dealership=ctx.dealership,
                public_id=vehicle_id,
            )
            .first()
        )

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        to_status = get_next_phase(vehicle)

        if not to_status:
            return Response(
                {"detail": "Vehicle cannot be advanced from current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not can_advance_vehicle(ctx, vehicle):
            return Response(
                {"detail": "You do not have permission to advance this vehicle."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = VehiclePhaseAdvanceSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        assignee = None
        assign_user_id = serializer.validated_data.get("assign_user_id")
        required_assignee_permission = ASSIGNEE_PERMISSION_FOR_PHASE.get(to_status)

        if assign_user_id and required_assignee_permission:
            membership = get_assignable_membership(
                dealership=ctx.dealership,
                user_public_id=assign_user_id,
                required_permission=required_assignee_permission,
            )

            if not membership:
                return Response(
                    {
                        "detail": "Assigned user is not eligible for this phase.",
                        "required_permission": required_assignee_permission,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            assignee = membership.user

        from_status, to_status, folder = advance_vehicle_phase(
            vehicle=vehicle,
            actor=request.user,
            assignee=assignee,
            note=serializer.validated_data.get("note", ""),
        )

        return Response(
            {
                "vehicle": VehicleDetailSerializer(vehicle).data,
                "transition": {
                    "from": from_status,
                    "to": to_status,
                    "assigned_to": (
                        {
                            "id": str(assignee.public_id),
                            "email": assignee.email,
                            "name": assignee.display_name,
                        }
                        if assignee
                        else None
                    ),
                    "destination_folder": (
                        {
                            "id": str(folder.public_id),
                            "name": folder.name,
                            "type": folder.type,
                        }
                        if folder
                        else None
                    ),
                },
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