# buying/views/buying.py

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from buying.models import BuyingDecision
from buying.serializers import BuyingDecisionSerializer, BuyingDecisionUpdateSerializer
from buying.services.buying import get_or_create_buying_decision, update_buying_decision
from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission
from hammer.models import HammerSession
from inventory.models import Vehicle


class VehicleBuyingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_BUYING):
            return Response(
                {"detail": "You do not have permission to view buying."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        decision = BuyingDecision.objects.filter(vehicle=vehicle).first()
        hammer_session = HammerSession.objects.filter(vehicle=vehicle).first()

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "decision": BuyingDecisionSerializer(decision).data if decision else None,
                "hammer": (
                    {
                        "id": hammer_session.public_id,
                        "status": hammer_session.status,
                        "est_cost_total": hammer_session.est_cost_total,
                        "est_time_total_minutes": hammer_session.est_time_total_minutes,
                    }
                    if hammer_session
                    else None
                ),
                "permissions": {
                    "can_update": has_permission(ctx, Permissions.MANAGE_BUYING),
                },
            }
        )

    def patch(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_BUYING):
            return Response(
                {"detail": "You do not have permission to update buying."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = BuyingDecisionUpdateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        decision, recon_payload = update_buying_decision(
            vehicle=vehicle,
            actor=request.user,
            decision_value=serializer.validated_data["decision"],
            notes=serializer.validated_data.get("notes", ""),
        )

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "decision": BuyingDecisionSerializer(decision).data,
                "recon": recon_payload,
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