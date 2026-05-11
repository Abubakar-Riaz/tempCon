# recon/views/recon.py

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import Vehicle, VehicleStatus
from inventory.services.vehicle_history import record_recon_status_updated
from recon.models import ReconCase, ReconStatus, WorkItem
from recon.serializers import (
    ReconCaseSerializer,
    ReconStatusUpdateSerializer,
    WorkItemSerializer,
)


class ReconCaseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_RECON):
            return Response(
                {"detail": "You do not have permission to view recon."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        recon_case = ReconCase.objects.filter(vehicle=vehicle).first()

        if not recon_case:
            return Response(
                {
                    "vehicle": _vehicle_payload(vehicle),
                    "recon_case": None,
                    "work_items": [],
                }
            )

        qs = (
            WorkItem.objects
            .select_related(
                "trade",
                "source_inspection_item",
                "assigned_vendor",
                "assigned_vendor__user",
            )
            .filter(recon_case=recon_case)
            .order_by("priority", "due_date", "created_at")
        )

        status_param = (request.query_params.get("status") or "").strip()
        trade_id = (request.query_params.get("trade_id") or "").strip()
        vendor_membership_id = (request.query_params.get("vendor_membership_id") or "").strip()

        if status_param:
            qs = qs.filter(status=status_param)

        if trade_id:
            qs = qs.filter(trade__public_id=trade_id)

        if vendor_membership_id:
            qs = qs.filter(assigned_vendor__public_id=vendor_membership_id)

        return Response(
            {
                "vehicle": _vehicle_payload(vehicle),
                "recon_case": ReconCaseSerializer(recon_case).data,
                "work_items": WorkItemSerializer(qs, many=True).data,
                "permissions": {
                    "can_update_status": has_permission(ctx, Permissions.MANAGE_RECON),
                    "can_assign_vendor": has_permission(ctx, Permissions.ASSIGN_RECON_WORK),
                },
            }
        )


class ReconStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_RECON):
            return Response(
                {"detail": "You do not have permission to update recon."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        recon_case = ReconCase.objects.select_for_update().filter(vehicle=vehicle).first()

        if not recon_case:
            return Response(
                {"detail": "Recon case not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ReconStatusUpdateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        new_recon_status = serializer.validated_data["status"]
        previous_vehicle_status = vehicle.status
        now = timezone.now()

        recon_case.status = new_recon_status
        recon_case.notes = serializer.validated_data.get("notes", recon_case.notes)

        if new_recon_status == ReconStatus.FAIL:
            recon_case.fail_reason = serializer.validated_data.get("reason", "")
            recon_case.closed_at = now
            vehicle.status = VehicleStatus.RECON_FAIL
            vehicle.recon_at = now
        else:
            recon_case.fail_reason = ""
            recon_case.closed_at = now
            vehicle.status = VehicleStatus.COMPLETE
            vehicle.complete_at = now

        recon_case.save(
            update_fields=[
                "status",
                "notes",
                "fail_reason",
                "closed_at",
                "updated_at",
            ]
        )

        vehicle.updated_by = request.user
        vehicle.save(
            update_fields=[
                "status",
                "recon_at",
                "complete_at",
                "updated_by",
                "updated_at",
            ]
        )

        record_recon_status_updated(
            vehicle=vehicle,
            recon_case=recon_case,
            actor=request.user,
            from_status=previous_vehicle_status,
            to_status=new_recon_status,
            reason=recon_case.fail_reason,
        )

        return Response(
            {
                "vehicle": _vehicle_payload(vehicle),
                "recon_case": ReconCaseSerializer(recon_case).data,
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


def _vehicle_payload(vehicle):
    return {
        "id": vehicle.public_id,
        "vin": vehicle.vin,
        "status": vehicle.status,
    }