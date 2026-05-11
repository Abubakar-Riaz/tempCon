# recon/views/work_items.py

from __future__ import annotations
from datetime import timezone

from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import DealershipMembership, MembershipStatus
from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import (
    build_access_context,
    get_membership_permissions,
    has_permission,
)

from inventory.models import Folder, FolderType, FolderVehicle, VehicleStatus
from inventory.services.vehicle_history import (
    record_recon_vendor_assigned,
    record_vehicle_added_to_folder,
)
from recon.models import WorkItem, WorkItemStatus
from recon.serializers import AssignVendorSerializer, WorkItemSerializer


class AssignVendorView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, work_item_id):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.ASSIGN_RECON_WORK):
            return Response(
                {"detail": "You do not have permission to assign recon work."},
                status=status.HTTP_403_FORBIDDEN,
            )

        work_item = (
            WorkItem.objects
            .select_for_update()
            .select_related(
                "trade",
                "source_inspection_item",
                "recon_case",
                "recon_case__vehicle",
                "recon_case__vehicle__dealership",
                "assigned_vendor",
                "assigned_vendor__user",
            )
            .filter(
                public_id=work_item_id,
                recon_case__vehicle__company=ctx.company,
                recon_case__vehicle__dealership=ctx.dealership,
            )
            .first()
        )

        if not work_item:
            return Response(
                {"detail": "Work item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AssignVendorSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)

        vendor_membership = _get_vendor_membership(
            dealership=ctx.dealership,
            membership_public_id=serializer.validated_data["vendor_membership_id"],
        )

        if not vendor_membership:
            return Response(
                {"detail": "Vendor membership not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        vendor_permissions = get_membership_permissions(vendor_membership)

        if Permissions.MANAGE_VENDOR_WORK not in vendor_permissions:
            return Response(
                {"detail": "Selected member does not have vendor work permission."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if "priority" in serializer.validated_data:
            work_item.priority = serializer.validated_data["priority"]

        if "due_date" in serializer.validated_data:
            work_item.due_date = serializer.validated_data["due_date"]

        if "notes" in serializer.validated_data:
            work_item.notes = serializer.validated_data["notes"]

        work_item.assigned_vendor = vendor_membership
        work_item.status = WorkItemStatus.IN_PROGRESS
        work_item.save(
            update_fields=[
                "assigned_vendor",
                "status",
                "priority",
                "due_date",
                "notes",
                "updated_at",
            ]
        )

        folder = _ensure_vendor_folder(
            work_item=work_item,
            vendor_membership=vendor_membership,
            actor=request.user,
        )

        record_recon_vendor_assigned(
            vehicle=work_item.recon_case.vehicle,
            work_item=work_item,
            vendor_membership=vendor_membership,
            actor=request.user,
        )

        return Response(
            {
                "work_item": WorkItemSerializer(work_item).data,
                "destination_folder": (
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


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )


def _get_vendor_membership(*, dealership, membership_public_id):
    return (
        DealershipMembership.objects
        .select_related("user", "company", "dealership")
        .filter(
            public_id=membership_public_id,
            dealership=dealership,
            status=MembershipStatus.ACTIVE,
        )
        .first()
    )


def _ensure_vendor_folder(*, work_item, vendor_membership, actor):
    vehicle = work_item.recon_case.vehicle
    today = timezone.localdate()
    user = vendor_membership.user

    folder, _ = Folder.objects.get_or_create(
        company=vehicle.company,
        dealership=vehicle.dealership,
        type=FolderType.AUTO_VENDOR_DAILY,
        date_bucket=today,
        created_by=user,
        defaults={
            "name": f"{today:%Y-%m-%d} - vendor - {user.email}",
        },
    )

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

    return folder