# vendors/views/work_items.py

from __future__ import annotations

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import Vehicle
from inventory.services.vehicle_history import (
    record_vendor_attachment_added,
    record_vendor_work_completed,
)
from recon.models import VendorAttachment, WorkItem, WorkItemStatus
from vendors.serializers import (
    VendorAttachmentSerializer,
    VendorAttachmentUploadSerializer,
    VendorWorkItemCompleteSerializer,
    VendorWorkItemSerializer,
)


class VendorWorkItemsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vehicle_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_VENDOR_WORK):
            return Response(
                {"detail": "You do not have permission to view vendor work."},
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
            WorkItem.objects
            .select_related(
                "trade",
                "recon_case",
                "recon_case__vehicle",
            )
            .annotate(attachments_count=Count("vendor_attachments"))
            .filter(
                assigned_vendor=ctx.membership,
                recon_case__vehicle=vehicle,
            )
            .order_by(
                "trade__label",
                "priority",
                "due_date",
                "created_at",
            )
        )

        status_value = (request.query_params.get("status") or "").strip()
        if status_value:
            qs = qs.filter(status=status_value)

        return Response(
            {
                "vehicle": {
                    "id": vehicle.public_id,
                    "vin": vehicle.vin,
                    "status": vehicle.status,
                },
                "results": VendorWorkItemSerializer(qs, many=True).data,
            }
        )


class VendorWorkItemCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, work_item_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_VENDOR_WORK):
            return Response(
                {"detail": "You do not have permission to complete vendor work."},
                status=status.HTTP_403_FORBIDDEN,
            )

        work_item = _get_vendor_work_item(ctx=ctx, work_item_id=work_item_id)

        if not work_item:
            return Response(
                {"detail": "Work item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if work_item.status == WorkItemStatus.DONE:
            return Response(
                {"detail": "Work item is already complete."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = VendorWorkItemCompleteSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        work_item.actual_cost = data.get("actual_cost", work_item.est_cost)
        work_item.actual_time_minutes = data.get(
            "actual_time_minutes",
            work_item.est_time_minutes,
        )
        work_item.completion_date = data.get(
            "completion_date",
            timezone.localdate(),
        )

        if "notes" in data:
            work_item.notes = data["notes"]

        work_item.status = WorkItemStatus.DONE
        work_item.save(
            update_fields=[
                "actual_cost",
                "actual_time_minutes",
                "completion_date",
                "notes",
                "status",
                "updated_at",
            ]
        )

        record_vendor_work_completed(
            vehicle=work_item.recon_case.vehicle,
            work_item=work_item,
            actor=request.user,
        )

        return Response(VendorWorkItemSerializer(work_item).data)


class VendorWorkItemAttachmentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @transaction.atomic
    def post(self, request, work_item_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.UPLOAD_VENDOR_ATTACHMENTS):
            return Response(
                {"detail": "You do not have permission to upload vendor attachments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        work_item = _get_vendor_work_item(ctx=ctx, work_item_id=work_item_id)

        if not work_item:
            return Response(
                {"detail": "Work item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = VendorAttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attachment = VendorAttachment.objects.create(
            work_item=work_item,
            uploaded_by_user=request.user,
            file=serializer.validated_data["file"],
            kind=serializer.validated_data.get("kind"),
            metadata=serializer.validated_data.get("metadata") or {},
        )

        record_vendor_attachment_added(
            vehicle=work_item.recon_case.vehicle,
            work_item=work_item,
            attachment=attachment,
            actor=request.user,
        )

        return Response(
            VendorAttachmentSerializer(attachment).data,
            status=status.HTTP_201_CREATED,
        )


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )


def _get_vendor_work_item(*, ctx, work_item_id):
    return (
        WorkItem.objects
        .select_related(
            "trade",
            "recon_case",
            "recon_case__vehicle",
        )
        .filter(
            public_id=work_item_id,
            assigned_vendor=ctx.membership,
            recon_case__vehicle__company=ctx.company,
            recon_case__vehicle__dealership=ctx.dealership,
        )
        .first()
    )