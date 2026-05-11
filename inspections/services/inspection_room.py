# inspections/realtime_utils.py

from __future__ import annotations

from asgiref.sync import sync_to_async

from core.authz.permissions import Permissions
from core.authz.resolver import build_access_context, has_permission
from inventory.models import Vehicle
from inspections.models import InspectionItem, InspectionItemStatus


def ws_error(code: str, message: str, fields: dict | None = None) -> dict:
    payload = {"code": code, "message": message}

    if fields:
        payload["fields"] = fields

    return payload


@sync_to_async
def db_resolve_vehicle_context(user, vehicle_public_id):
    vehicle = (
        Vehicle.objects
        .select_related("company", "dealership")
        .filter(
            public_id=vehicle_public_id,
            dealership__is_active=True,
            company__is_active=True,
        )
        .first()
    )

    if not vehicle:
        return None, None

    from accounts.models import DealershipMembership, MembershipStatus

    membership = (
        DealershipMembership.objects
        .select_related("user", "dealership", "company")
        .filter(
            user=user,
            dealership=vehicle.dealership,
            status=MembershipStatus.ACTIVE,
        )
        .first()
    )

    if not membership:
        return vehicle, None

    ctx = build_access_context(
        user=user,
        membership=membership,
        dealership=vehicle.dealership,
        subscription=getattr(vehicle.company, "subscription", None),
    )

    return vehicle, ctx


@sync_to_async
def db_can_view_inspection(ctx) -> bool:
    return has_permission(ctx, Permissions.VIEW_INSPECTIONS)


@sync_to_async
def db_can_edit_inspection(ctx) -> bool:
    return has_permission(ctx, Permissions.MANAGE_INSPECTIONS)


@sync_to_async
def db_build_inspection_snapshot(vehicle, *, compact: bool = True) -> dict:
    inspection = vehicle.inspections.order_by("-started_at", "-id").first()

    if not inspection:
        return {
            "inspection": None,
            "trades": [],
            "summary": {
                "status": None,
                "items_total": 0,
                "items_ok": 0,
                "items_needs_attention": 0,
            },
        }

    items = (
        inspection.items
        .select_related("trade")
        .order_by("trade__order_index", "trade__label", "label")
    )

    grouped = {}

    for item in items:
        trade_key = item.trade.key if item.trade_id else "unassigned"

        grouped.setdefault(
            trade_key,
            {
                "key": trade_key,
                "label": item.trade.label if item.trade_id else "Unassigned",
                "items": [],
            },
        )

        grouped[trade_key]["items"].append(
            {
                "id": str(item.public_id),
                "label": item.label,
                "status": item.status,
                "notes": item.notes,
                "attachments_count": item.item_attachments.count(),
            }
        )

    return {
        "inspection": {
            "id": str(inspection.public_id),
            "status": inspection.status,
            "started_at": inspection.started_at.isoformat() if inspection.started_at else None,
            "completed_at": inspection.completed_at.isoformat() if inspection.completed_at else None,
        },
        "trades": list(grouped.values()),
        "summary": {
            "status": inspection.status,
            "items_total": inspection.items_total,
            "items_ok": inspection.items_ok,
            "items_needs_attention": inspection.items_needs_attention,
        },
    }


@sync_to_async
def db_item_status_set(user, vehicle, item_public_id, status_value):
    inspection = vehicle.inspections.order_by("-started_at", "-id").first()

    if not inspection:
        raise ValueError("INSPECTION_NOT_FOUND")

    item = (
        InspectionItem.objects
        .select_related("trade")
        .filter(
            inspection=inspection,
            public_id=item_public_id,
        )
        .first()
    )

    if not item:
        raise ValueError("ITEM_NOT_FOUND")

    valid_statuses = {value for value, _ in InspectionItemStatus.choices}

    if status_value not in valid_statuses:
        raise ValueError("INVALID_STATUS")

    item.status = status_value
    item.save(update_fields=["status", "updated_at"])

    inspection.items_total = inspection.items.count()
    inspection.items_ok = inspection.items.filter(status=InspectionItemStatus.OK).count()
    inspection.items_needs_attention = inspection.items.filter(
        status=InspectionItemStatus.NEEDS_ATTENTION,
    ).count()
    inspection.save(
        update_fields=[
            "items_total",
            "items_ok",
            "items_needs_attention",
            "updated_at",
        ]
    )

    return {
        "id": str(item.public_id),
        "label": item.label,
        "status": item.status,
        "trade": {
            "key": item.trade.key if item.trade_id else None,
            "label": item.trade.label if item.trade_id else None,
        },
        "summary": {
            "items_total": inspection.items_total,
            "items_ok": inspection.items_ok,
            "items_needs_attention": inspection.items_needs_attention,
        },
        "by": {
            "id": str(user.public_id),
            "email": user.email,
        },
    }


@sync_to_async
def db_item_note_set(user, vehicle, item_public_id, body):
    inspection = vehicle.inspections.order_by("-started_at", "-id").first()

    if not inspection:
        raise ValueError("INSPECTION_NOT_FOUND")

    item = InspectionItem.objects.filter(
        inspection=inspection,
        public_id=item_public_id,
    ).select_related("trade").first()

    if not item:
        raise ValueError("ITEM_NOT_FOUND")

    item.notes = body or ""
    item.save(update_fields=["notes", "updated_at"])

    return {
        "id": str(item.public_id),
        "label": item.label,
        "notes": item.notes,
        "trade": {
            "key": item.trade.key if item.trade_id else None,
            "label": item.trade.label if item.trade_id else None,
        },
        "by": {
            "id": str(user.public_id),
            "email": user.email,
        },
    }