# inspections/views/attachments.py

from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import Attachment, AttachmentPhase
from inspections.models import InspectionItem, InspectionItemAttachment
from inspections.serializers import (
    InspectionAttachmentSerializer,
    InspectionItemAttachmentUploadSerializer,
)
from inventory.services.vehicle_history import record_inspection_attachment_added


class InspectionItemAttachmentView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, item_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INSPECTIONS):
            return Response(
                {"detail": "You do not have permission to view inspection attachments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        item = _get_item(ctx=ctx, item_id=item_id)

        if not item:
            return Response(
                {"detail": "Inspection item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        links = (
            InspectionItemAttachment.objects
            .select_related("attachment", "attachment__uploaded_by")
            .filter(item=item)
            .order_by("-created_at")
        )

        return Response(
            {
                "item": {
                    "id": item.public_id,
                    "label": item.label,
                    "trade": item.trade_label,
                },
                "attachments": InspectionAttachmentSerializer(links, many=True).data,
            }
        )

    @transaction.atomic
    def post(self, request, item_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_INSPECTIONS):
            return Response(
                {"detail": "You do not have permission to upload inspection attachments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        item = _get_item(ctx=ctx, item_id=item_id)

        if not item:
            return Response(
                {"detail": "Inspection item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = InspectionItemAttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        caption = (serializer.validated_data.get("caption") or "").strip()
        metadata = serializer.validated_data.get("metadata") or {}

        attachment = Attachment.objects.create(
            vehicle=item.inspection.vehicle,
            uploaded_by=request.user,
            file=serializer.validated_data["file"],
            phase_tag=AttachmentPhase.INSPECTION,
            metadata={
                **metadata,
                "caption": caption,
                "inspection_item_id": str(item.public_id),
            },
        )

        link, _ = InspectionItemAttachment.objects.get_or_create(
            item=item,
            attachment=attachment,
        )

        item.save(update_fields=["updated_at"])

        record_inspection_attachment_added(
            vehicle=item.inspection.vehicle,
            item=item,
            attachment=attachment,
            actor=request.user,
        )

        return Response(
            InspectionAttachmentSerializer(link).data,
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


def _get_item(*, ctx, item_id):
    return (
        InspectionItem.objects
        .select_related(
            "trade",
            "inspection",
            "inspection__vehicle",
        )
        .filter(
            public_id=item_id,
            inspection__vehicle__company=ctx.company,
            inspection__vehicle__dealership=ctx.dealership,
        )
        .first()
    )