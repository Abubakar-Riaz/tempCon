# inventory/services/vehicle_phases.py

from __future__ import annotations

from django.utils import timezone

from accounts.models import DealershipMembership, MembershipStatus
from core.authz.permissions import Permissions
from core.authz.resolver import has_permission

from inventory.models import (
    Folder,
    FolderType,
    FolderVehicle,
    HistoryEventKind,
    VehicleStatus,
)
from inventory.services.vehicle_history import (
    record_vehicle_added_to_folder,
    record_vehicle_status_changed,
)


SUCCESSOR = {
    VehicleStatus.UPLOADED: VehicleStatus.VHR,
    VehicleStatus.VHR: VehicleStatus.INSPECTION,
    VehicleStatus.INSPECTION: VehicleStatus.HAMMER,
    VehicleStatus.HAMMER: VehicleStatus.BUYING,
    VehicleStatus.BUYING: VehicleStatus.RECON,
    VehicleStatus.RECON: VehicleStatus.COMPLETE,
}

TRANSITION_PERMISSION = {
    VehicleStatus.UPLOADED: Permissions.MANAGE_INVENTORY,
    VehicleStatus.VHR: Permissions.MANAGE_VHR,
    VehicleStatus.INSPECTION: Permissions.MANAGE_INSPECTIONS,
    VehicleStatus.HAMMER: Permissions.MANAGE_HAMMER,
    VehicleStatus.BUYING: Permissions.MANAGE_BUYING,
    VehicleStatus.RECON: Permissions.MANAGE_RECON,
}

ASSIGNEE_PERMISSION_FOR_PHASE = {
    VehicleStatus.INSPECTION: Permissions.MANAGE_INSPECTIONS,
    VehicleStatus.HAMMER: Permissions.MANAGE_HAMMER,
    VehicleStatus.BUYING: Permissions.MANAGE_BUYING,
    VehicleStatus.RECON: Permissions.MANAGE_RECON,
    VehicleStatus.COMPLETE: Permissions.MANAGE_RECON,
}

PHASE_TIMESTAMP_FIELD = {
    VehicleStatus.VHR: "vhr_at",
    VehicleStatus.INSPECTION: "inspection_at",
    VehicleStatus.HAMMER: "hammer_at",
    VehicleStatus.BUYING: "buying_at",
    VehicleStatus.RECON: "recon_at",
    VehicleStatus.COMPLETE: "complete_at",
}

AUTO_FOLDER_TYPE_FOR_PHASE = {
    VehicleStatus.INSPECTION: FolderType.AUTO_INSPECTION_DAILY,
    VehicleStatus.BUYING: FolderType.AUTO_BUYING_DAILY,
    VehicleStatus.RECON: FolderType.AUTO_RECON_DAILY,
}

HISTORY_KIND_FOR_PHASE = {
    VehicleStatus.VHR: HistoryEventKind.VHR_STARTED,
    VehicleStatus.INSPECTION: HistoryEventKind.INSPECTION_STARTED,
    VehicleStatus.HAMMER: HistoryEventKind.HAMMER_STARTED,
    VehicleStatus.BUYING: HistoryEventKind.BUYING_DECIDED,
    VehicleStatus.RECON: HistoryEventKind.RECON_STARTED,
    VehicleStatus.COMPLETE: HistoryEventKind.VEHICLE_COMPLETED,
}


def get_next_phase(vehicle):
    return SUCCESSOR.get(vehicle.status)


def can_advance_vehicle(ctx, vehicle) -> bool:
    permission = TRANSITION_PERMISSION.get(vehicle.status)
    return bool(permission and has_permission(ctx, permission))


def get_assignable_membership(*, dealership, user_public_id, required_permission: str):
    from core.authz.resolver import get_membership_permissions

    membership = (
        DealershipMembership.objects
        .select_related("user", "dealership", "company")
        .filter(
            user__public_id=user_public_id,
            dealership=dealership,
            status=MembershipStatus.ACTIVE,
        )
        .first()
    )

    if not membership:
        return None

    if required_permission not in get_membership_permissions(membership):
        return None

    return membership


def ensure_phase_folder(*, vehicle, phase, assignee, actor):
    folder_type = AUTO_FOLDER_TYPE_FOR_PHASE.get(phase)

    if not folder_type or not assignee:
        return None

    today = timezone.localdate()
    name = f"{today:%Y-%m-%d} - {phase} - {assignee.email}"

    folder, _ = Folder.objects.get_or_create(
        company=vehicle.company,
        dealership=vehicle.dealership,
        type=folder_type,
        date_bucket=today,
        created_by=assignee,
        defaults={"name": name},
    )

    _, linked = FolderVehicle.objects.get_or_create(
        folder=folder,
        vehicle=vehicle,
        defaults={"added_by": actor},
    )

    if linked:
        record_vehicle_added_to_folder(
            vehicle=vehicle,
            folder=folder,
            actor=actor,
        )

    return folder


def advance_vehicle_phase(*, vehicle, actor, assignee=None, note: str = ""):
    from_status = vehicle.status
    to_status = get_next_phase(vehicle)

    if not to_status:
        raise ValueError("Vehicle cannot be advanced from current status.")

    timestamp_field = PHASE_TIMESTAMP_FIELD.get(to_status)

    update_fields = [
        "status",
        "updated_by",
        "updated_at",
    ]

    vehicle.status = to_status
    vehicle.updated_by = actor

    if timestamp_field:
        setattr(vehicle, timestamp_field, timezone.now())
        update_fields.append(timestamp_field)

    vehicle.save(update_fields=update_fields)

    folder = ensure_phase_folder(
        vehicle=vehicle,
        phase=to_status,
        assignee=assignee,
        actor=actor,
    )

    record_vehicle_status_changed(
        vehicle=vehicle,
        actor=actor,
        from_status=from_status,
        to_status=to_status,
        kind=HISTORY_KIND_FOR_PHASE.get(to_status, HistoryEventKind.STATUS_CHANGED),
        title=f"Vehicle advanced to {vehicle.get_status_display()}",
        payload={
            "note": note or "",
            "assigned_to": (
                {
                    "id": str(assignee.public_id),
                    "email": assignee.email,
                    "name": assignee.display_name,
                }
                if assignee
                else None
            ),
            "folder": (
                {
                    "id": str(folder.public_id),
                    "name": folder.name,
                    "type": folder.type,
                }
                if folder
                else None
            ),
        },
    )

    return from_status, to_status, folder