# inventory/views/vehicles.py

from __future__ import annotations

import csv
import io

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils.dateparse import parse_datetime

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.features import Features
from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_feature, has_permission

from inventory.imports.constants import CSV_HEADERS, HEADER_MAP, IMPORT_UPDATE_FIELDS
from inventory.models import Folder, FolderVehicle, Vehicle, VehicleSource, VehicleStatus
from inventory.serializers.vehicles import (
    VehicleCreateUpdateSerializer,
    VehicleDetailSerializer,
    VehicleListItemSerializer,
)
from inventory.services.vehicle_history import (
    record_vehicle_added_to_folder,
    record_vehicle_created,
    record_vehicle_updated,
)
from inventory.services.vehicle_helpers import (
    _parse_start_time,
    _validate_vin,
)


class VehiclesPagination(PageNumberPagination):
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


def _get_folder(*, ctx, folder_id):
    return Folder.objects.filter(
        company=ctx.company,
        dealership=ctx.dealership,
        public_id=folder_id,
    ).first()


def _get_vehicle(*, ctx, vehicle_id):
    return (
        Vehicle.objects
        .select_related("dealership", "created_by", "updated_by")
        .filter(
            company=ctx.company,
            dealership=ctx.dealership,
            public_id=vehicle_id,
        )
        .first()
    )


def _link_vehicle_to_folder(*, vehicle, folder, actor):
    _, created = FolderVehicle.objects.get_or_create(
        folder=folder,
        vehicle=vehicle,
        defaults={"added_by": actor},
    )

    if created:
        record_vehicle_added_to_folder(
            vehicle=vehicle,
            folder=folder,
            actor=actor,
        )


def _apply_vehicle_filters(qs, params):
    status_value = (params.get("status") or "").strip()

    if status_value:
        valid_statuses = {choice for choice, _ in VehicleStatus.choices}

        if status_value not in valid_statuses:
            return None, Response(
                {
                    "detail": "Invalid status.",
                    "valid_statuses": sorted(valid_statuses),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = qs.filter(status=status_value)

    vin = (params.get("vin") or "").strip().upper()
    if vin:
        qs = qs.filter(vin__iexact=vin)

    stock_no = (params.get("stock_no") or "").strip()
    if stock_no:
        qs = qs.filter(stock_no__iexact=stock_no)

    since = (params.get("since") or "").strip()
    if since:
        dt = parse_datetime(since)

        if not dt:
            return None, Response(
                {"detail": "since must be an ISO 8601 datetime."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = qs.filter(updated_at__gte=dt)

    until = (params.get("until") or "").strip()
    if until:
        dt = parse_datetime(until)

        if not dt:
            return None, Response(
                {"detail": "until must be an ISO 8601 datetime."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = qs.filter(updated_at__lt=dt)

    search = (params.get("q") or "").strip()
    if search:
        qs = qs.filter(
            Q(vin__icontains=search)
            | Q(stock_no__icontains=search)
            | Q(make__icontains=search)
            | Q(model__icontains=search)
            | Q(trim__icontains=search)
            | Q(main_description__icontains=search)
            | Q(secondary_description__icontains=search)
        )

    ordering = (params.get("ordering") or "-updated_at").strip()
    allowed_ordering = {
        "updated_at",
        "-updated_at",
        "created_at",
        "-created_at",
        "year",
        "-year",
        "make",
        "-make",
        "model",
        "-model",
        "status",
        "-status",
    }

    ordering_fields = [field.strip() for field in ordering.split(",") if field.strip()]

    if any(field not in allowed_ordering for field in ordering_fields):
        return None, Response(
            {
                "detail": "Invalid ordering.",
                "valid_ordering": sorted(allowed_ordering),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    return qs.order_by(*ordering_fields), None


def _row_to_vehicle_payload(row: dict) -> dict:
    payload = {}

    for raw_key, raw_value in row.items():
        key = (raw_key or "").strip().lower()

        if key in HEADER_MAP:
            payload[HEADER_MAP[key]] = (raw_value or "").strip()

    payload["vin"] = _validate_vin(payload.get("vin"))

    if payload.get("auction_start_at"):
        parsed = _parse_start_time(payload["auction_start_at"])

        if not parsed:
            raise ValueError("Invalid Start Time.")

        payload["auction_start_at"] = parsed
    else:
        payload["auction_start_at"] = None

    serializer = VehicleCreateUpdateSerializer(data=payload)
    serializer.is_valid(raise_exception=True)

    return serializer.validated_data


class FolderVehicleListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = VehiclesPagination

    def get(self, request, folder_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INVENTORY):
            return Response(
                {"detail": "You do not have permission to view inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        folder = _get_folder(ctx=ctx, folder_id=folder_id)

        if not folder:
            return Response(
                {"detail": "Folder not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = (
            Vehicle.objects
            .select_related("dealership", "updated_by")
            .filter(
                company=ctx.company,
                dealership=ctx.dealership,
                folder_links__folder=folder,
            )
        )

        qs, error = _apply_vehicle_filters(qs, request.query_params)

        if error:
            return error

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        return paginator.get_paginated_response(
            VehicleListItemSerializer(page, many=True).data
        )

    @transaction.atomic
    def post(self, request, folder_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_INVENTORY):
            return Response(
                {"detail": "You do not have permission to manage inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        folder = _get_folder(ctx=ctx, folder_id=folder_id)

        if not folder:
            return Response(
                {"detail": "Folder not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VehicleCreateUpdateSerializer(
            data=request.data,
            context={
                "request": request,
                "company": ctx.company,
            },
        )
        serializer.is_valid(raise_exception=True)

        payload = serializer.validated_data
        vehicle_status = payload.pop("status", None) or VehicleStatus.UPLOADED

        try:
            vehicle = Vehicle.objects.create(
                company=ctx.company,
                dealership=ctx.dealership,
                source=VehicleSource.MANUAL,
                status=vehicle_status,
                created_by=request.user,
                updated_by=request.user,
                **payload,
            )
        except IntegrityError:
            return Response(
                {"detail": "Vehicle already exists."},
                status=status.HTTP_409_CONFLICT,
            )

        _link_vehicle_to_folder(
            vehicle=vehicle,
            folder=folder,
            actor=request.user,
        )

        record_vehicle_created(
            vehicle=vehicle,
            actor=request.user,
            source=VehicleSource.MANUAL,
        )

        return Response(
            VehicleListItemSerializer(vehicle).data,
            status=status.HTTP_201_CREATED,
        )


class VehicleDetailUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INVENTORY):
            return Response(
                {"detail": "You do not have permission to view inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            VehicleDetailSerializer(
                vehicle,
                context={
                    "read_only_map": {
                        "vehicle_info": has_permission(ctx, Permissions.MANAGE_INVENTORY),
                        "vhr": has_permission(ctx, Permissions.MANAGE_VHR),
                        "inspection": has_permission(ctx, Permissions.MANAGE_INSPECTIONS),
                        "hammer": has_permission(ctx, Permissions.MANAGE_HAMMER),
                        "buying": has_permission(ctx, Permissions.MANAGE_BUYING),
                        "recon": has_permission(ctx, Permissions.MANAGE_RECON),
                    }
                },
            ).data
        )

    @transaction.atomic
    def patch(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_INVENTORY):
            return Response(
                {"detail": "You do not have permission to manage inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        vehicle = _get_vehicle(ctx=ctx, vehicle_id=vehicle_id)

        if not vehicle:
            return Response(
                {"detail": "Vehicle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VehicleCreateUpdateSerializer(
            instance=vehicle,
            data=request.data,
            partial=True,
            context={
                "request": request,
                "company": ctx.company,
            },
        )
        serializer.is_valid(raise_exception=True)

        changed_fields = []

        for field, value in serializer.validated_data.items():
            if field == "vin":
                continue

            if getattr(vehicle, field) != value:
                setattr(vehicle, field, value)
                changed_fields.append(field)

        if changed_fields:
            vehicle.updated_by = request.user
            vehicle.save(update_fields=[*changed_fields, "updated_by", "updated_at"])

            record_vehicle_updated(
                vehicle=vehicle,
                actor=request.user,
                changed_fields=changed_fields,
            )

        return Response(VehicleDetailSerializer(vehicle).data)


class FolderVehicleImportView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, folder_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.IMPORT_VEHICLES):
            return Response(
                {"detail": "You do not have permission to import vehicles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not has_feature(ctx, Features.CSV_IMPORT):
            return Response(
                {"detail": "CSV import is not available for this subscription."},
                status=status.HTTP_403_FORBIDDEN,
            )

        folder = _get_folder(ctx=ctx, folder_id=folder_id)

        if not folder:
            return Response(
                {"detail": "Folder not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            return Response(
                {"detail": "CSV file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        on_conflict = (request.query_params.get("on_conflict") or "skip").strip().lower()
        dry_run = (request.query_params.get("dry_run") or "").strip().lower() == "true"

        if on_conflict not in {"skip", "update", "error"}:
            return Response(
                {"detail": "on_conflict must be one of: skip, update, error."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            text = io.TextIOWrapper(uploaded_file, encoding="utf-8-sig")
            reader = csv.DictReader(text)
        except Exception:
            return Response(
                {"detail": "Invalid CSV file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not reader.fieldnames or not any(h.strip().lower() == "vin" for h in reader.fieldnames):
            return Response(
                {"detail": "CSV must include a Vin header."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for row_number, row in enumerate(reader, start=2):
            try:
                payload = _row_to_vehicle_payload(row)
                vin = payload["vin"]

                existing = Vehicle.objects.filter(
                    company=ctx.company,
                    vin=vin,
                ).first()

                if existing:
                    if on_conflict == "error":
                        return Response(
                            {
                                "detail": "Duplicate VIN found.",
                                "row": row_number,
                                "vin": vin,
                            },
                            status=status.HTTP_409_CONFLICT,
                        )

                    if on_conflict == "skip":
                        skipped += 1
                        continue

                    if not dry_run:
                        changed_fields = []

                        for field in IMPORT_UPDATE_FIELDS:
                            if field in payload and getattr(existing, field) != payload[field]:
                                setattr(existing, field, payload[field])
                                changed_fields.append(field)

                        if changed_fields:
                            existing.updated_by = request.user
                            existing.save(
                                update_fields=[
                                    *changed_fields,
                                    "updated_by",
                                    "updated_at",
                                ]
                            )

                            record_vehicle_updated(
                                vehicle=existing,
                                actor=request.user,
                                changed_fields=changed_fields,
                            )

                        _link_vehicle_to_folder(
                            vehicle=existing,
                            folder=folder,
                            actor=request.user,
                        )

                    updated += 1
                    continue

                if not dry_run:
                    vehicle = Vehicle.objects.create(
                        company=ctx.company,
                        dealership=ctx.dealership,
                        source=VehicleSource.CSV,
                        status=VehicleStatus.UPLOADED,
                        created_by=request.user,
                        updated_by=request.user,
                        **payload,
                    )

                    _link_vehicle_to_folder(
                        vehicle=vehicle,
                        folder=folder,
                        actor=request.user,
                    )

                    record_vehicle_created(
                        vehicle=vehicle,
                        actor=request.user,
                        source=VehicleSource.CSV,
                    )

                created += 1

            except Exception as exc:
                errors.append(
                    {
                        "row": row_number,
                        "message": str(exc),
                    }
                )

        return Response(
            {
                "summary": {
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "errors": len(errors),
                    "dry_run": dry_run,
                    "on_conflict": on_conflict,
                },
                "errors": errors[:50],
            }
        )


class VehicleImportTemplateDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.IMPORT_VEHICLES):
            return Response(
                {"detail": "You do not have permission to import vehicles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_HEADERS)

        response = HttpResponse(
            buffer.getvalue(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="vehicle_import_template.csv"'

        return response