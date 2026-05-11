# inventory/views/vin_scanner.py

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import (
    resolve_request_dealership_context,
)
from core.authz.resolver import (
    build_access_context,
    has_permission,
)

from inventory.models import (
    Folder,
    FolderType,
    FolderVehicle,
    HistoryEvent,
    HistoryEventKind,
    Vehicle,
    VehicleSource,
    VehicleStatus,
)
from inventory.serializers.vin_scanner import (
    VinQuickAddSerializer,
    VinSearchQuerySerializer,
)


def _normalize_vin(vin: str) -> str:
    return (vin or "").strip().upper()


def _validate_vin(vin: str) -> str | None:
    if len(vin) != 17:
        return "VIN must be exactly 17 characters."
    return None


def _vehicle_folder(vehicle: Vehicle):
    return (
        Folder.objects
        .filter(folder_links__vehicle=vehicle)
        .order_by("created_at")
        .first()
    )


def _create_scan_folder(*, dealership, user) -> Folder:
    now = timezone.localtime()
    return Folder.objects.create(
        company=dealership.company,
        dealership=dealership,
        name=f"VIN Scan - {now:%Y-%m-%d %H:%M}",
        type=FolderType.MANUAL,
        created_by=user,
    )


def _create_vehicle_history(vehicle: Vehicle, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        company=vehicle.company,
        dealership=vehicle.dealership,
        actor=actor,
        kind=HistoryEventKind.VEHICLE_CREATED,
        to_status=vehicle.status,
        title="Vehicle created",
        payload={
            "source": vehicle.source,
            "vin": vehicle.vin,
        },
    )


class VehicleVinSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw_ctx = resolve_request_dealership_context(request)

        ctx = build_access_context(
            user=raw_ctx.user,
            membership=raw_ctx.membership,
            dealership=raw_ctx.dealership,
            subscription=raw_ctx.subscription,
        )

        if not has_permission(ctx, Permissions.VIEW_INVENTORY):
            return Response(
                {"detail": "You do not have permission to view inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = VinSearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        vin = _normalize_vin(serializer.validated_data["vin"])

        error = _validate_vin(vin)
        if error:
            return Response(
                {"detail": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        vehicle = (
            Vehicle.objects
            .select_related("dealership")
            .filter(
                company=ctx.company,
                vin=vin,
            )
            .first()
        )

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        folder = _vehicle_folder(vehicle)

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                    "year": vehicle.year,
                    "make": vehicle.make,
                    "model": vehicle.model,
                    "trim": vehicle.trim,
                    "dealership": {
                        "id": vehicle.dealership.public_id,
                        "name": vehicle.dealership.name,
                    },
                },
                "folder": (
                    {
                        "id": folder.public_id,
                        "name": folder.name,
                        "type": folder.type,
                    }
                    if folder
                    else None
                ),
            }
        )


class VehicleVinQuickAddView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        raw_ctx = resolve_request_dealership_context(request)

        ctx = build_access_context(
            user=raw_ctx.user,
            membership=raw_ctx.membership,
            dealership=raw_ctx.dealership,
            subscription=raw_ctx.subscription,
        )

        if not has_permission(ctx, Permissions.MANAGE_INVENTORY):
            return Response(
                {"detail": "You do not have permission to manage inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = VinQuickAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vin = _normalize_vin(serializer.validated_data["vin"])

        error = _validate_vin(vin)
        if error:
            return Response(
                {"detail": error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = (
            Vehicle.objects
            .select_related("dealership")
            .filter(
                company=ctx.company,
                vin=vin,
            )
            .first()
        )

        if existing:
            return Response(
                {
                    "detail": "Vehicle already exists.",
                    "vehicle_id": existing.public_id,
                    "dealership_id": existing.dealership.public_id,
                },
                status=status.HTTP_409_CONFLICT,
            )

        vehicle_payload = serializer.validated_data.get("vehicle") or {}

        vehicle_fields = {
            field.name
            for field in Vehicle._meta.fields
        }

        safe_payload = {
            key: value
            for key, value in vehicle_payload.items()
            if key in vehicle_fields
        }

        try:
            vehicle = Vehicle.objects.create(
                company=ctx.company,
                dealership=ctx.dealership,
                vin=vin,
                source=VehicleSource.MANUAL,
                status=VehicleStatus.UPLOADED,
                created_by=request.user,
                updated_by=request.user,
                **safe_payload,
            )

            folder = _create_scan_folder(
                dealership=ctx.dealership,
                user=request.user,
            )

            FolderVehicle.objects.create(
                folder=folder,
                vehicle=vehicle,
                added_by=request.user,
                is_primary=True,
            )

            _create_vehicle_history(
                vehicle=vehicle,
                actor=request.user,
            )

        except IntegrityError:
            return Response(
                {"detail": "Vehicle already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "folder": {
                    "id": folder.public_id,
                    "name": folder.name,
                    "type": folder.type,
                },
            },
            status=status.HTTP_201_CREATED,
        )