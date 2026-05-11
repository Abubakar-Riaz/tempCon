# inventory/views/vhr.py

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

from inventory.models import (
    HistoryEventKind,
    Vehicle,
    VehicleHistoryReport,
    VehicleStatus,
)
from inventory.serializers.vhr import (
    VHRUpdateSerializer,
    build_required_snapshot,
    build_vhr_payload,
    coerce_vhr_value,
    get_effective_vhr_config,
)
from inventory.services.vehicle_history import record_vehicle_status_changed


class VehicleVHRView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_VHR):
            return Response(
                {"detail": "You do not have permission to view VHR."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            build_vhr_payload(
                vehicle=vehicle,
                company=ctx.company,
                dealership=ctx.dealership,
            )
        )

    @transaction.atomic
    def patch(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_VHR):
            return Response(
                {"detail": "You do not have permission to update VHR."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VHRUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        incoming = serializer.validated_data["data"]
        config = get_effective_vhr_config(
            company=ctx.company,
            dealership=ctx.dealership,
        )

        config_by_key = {
            field["key"]: field
            for field in config
        }

        errors = {}
        cleaned = {}

        for key, value in incoming.items():
            field = config_by_key.get(key)

            if not field:
                continue

            try:
                cleaned[key] = coerce_vhr_value(
                    field=field,
                    value=value,
                )
            except Exception as exc:
                errors[key] = [str(exc)]

        if errors:
            return Response(
                {"detail": "Invalid VHR data.", "fields": errors},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        report, _ = VehicleHistoryReport.objects.get_or_create(
            vehicle=vehicle,
            defaults={
                "created_by": request.user,
                "data": {},
                "required_config_snapshot": build_required_snapshot(config),
            },
        )

        before_status = vehicle.status
        before_data = report.data or {}

        report.data = {
            **before_data,
            **cleaned,
        }

        if not report.required_config_snapshot:
            report.required_config_snapshot = build_required_snapshot(config)

        report.save()

        now = timezone.now()

        vehicle.vhr_at = now
        vehicle.updated_by = request.user

        if vehicle.status == VehicleStatus.UPLOADED:
            vehicle.status = VehicleStatus.VHR

        vehicle.save(
            update_fields=[
                "vhr_at",
                "updated_by",
                "status",
                "updated_at",
            ]
        )

        changed_keys = [
            key
            for key, value in cleaned.items()
            if before_data.get(key) != value
        ]

        if before_status != vehicle.status:
            record_vehicle_status_changed(
                vehicle=vehicle,
                actor=request.user,
                from_status=before_status,
                to_status=vehicle.status,
                kind=HistoryEventKind.VHR_STARTED,
                title="VHR started",
                payload={"changed_vhr_fields": changed_keys},
            )
        elif changed_keys:
            record_vehicle_status_changed(
                vehicle=vehicle,
                actor=request.user,
                from_status=vehicle.status,
                to_status=vehicle.status,
                kind=HistoryEventKind.VHR_COMPLETED,
                title="VHR updated",
                payload={"changed_vhr_fields": changed_keys},
            )

        return Response(
            build_vhr_payload(
                vehicle=vehicle,
                company=ctx.company,
                dealership=ctx.dealership,
            )
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