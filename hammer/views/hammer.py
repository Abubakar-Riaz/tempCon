# hammer/views/hammer.py

from __future__ import annotations

from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from hammer.models import HammerSession
from hammer.serializers import HammerSessionSerializer, HammerUpsertSerializer
from hammer.services.hammer import get_or_create_hammer_session, upsert_hammer_values
from inventory.models import Vehicle


class VehicleHammerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_HAMMER):
            return Response(
                {"detail": "You do not have permission to view hammer."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        session = HammerSession.objects.filter(vehicle=vehicle).first()

        if not session:
            return Response(
                {
                    "vehicle": {
                        "id": vehicle.public_id,
                        "vin": vehicle.vin,
                        "status": vehicle.status,
                    },
                    "session": None,
                }
            )

        session.lines_with_items = _session_lines(session)

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "session": HammerSessionSerializer(
                    session,
                    context={
                        "permissions": {
                            "can_update": has_permission(ctx, Permissions.MANAGE_HAMMER),
                        }
                    },
                ).data,
            }
        )

    @transaction.atomic
    def patch(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_HAMMER):
            return Response(
                {"detail": "You do not have permission to update hammer."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = HammerUpsertSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        session = get_or_create_hammer_session(
            vehicle=vehicle,
            manager=request.user,
        )

        try:
            session = upsert_hammer_values(
                session=session,
                lines=serializer.validated_data.get("lines") or [],
                notes=serializer.validated_data.get("notes"),
                calculator=serializer.validated_data.get("calculator"),
                finalize=serializer.validated_data.get("finalize", False),
                actor=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        session.lines_with_items = _session_lines(session)

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "session": HammerSessionSerializer(
                    session,
                    context={
                        "permissions": {
                            "can_update": has_permission(ctx, Permissions.MANAGE_HAMMER),
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


def _get_vehicle(*, ctx, vehicle_id):
    return Vehicle.objects.filter(
        company=ctx.company,
        dealership=ctx.dealership,
        public_id=vehicle_id,
    ).first()


def _session_lines(session):
    return (
        session.lines
        .select_related("inspection_item", "inspection_item__trade")
        .order_by(
            "inspection_item__trade__order_index",
            "inspection_item__trade_label",
            "inspection_item__label",
        )
    )