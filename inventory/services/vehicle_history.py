# inventory/services/vehicle_history.py

from inventory.models import HistoryEvent, HistoryEventKind


def record_vehicle_created(*, vehicle, actor, source: str):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.VEHICLE_CREATED,
        to_status=vehicle.status,
        title="Vehicle created",
        payload={
            "source": source,
            "vin": vehicle.vin,
        },
    )


def record_vehicle_updated(*, vehicle, actor, changed_fields: list[str]):
    if not changed_fields:
        return

    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.OTHER,
        title="Vehicle updated",
        payload={
            "changed_fields": changed_fields,
        },
    )


def record_vehicle_added_to_folder(*, vehicle, folder, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.FOLDER_ADDED,
        title="Vehicle added to folder",
        payload={
            "folder_id": str(folder.public_id),
            "folder_name": folder.name,
        },
    )


def record_vehicle_status_changed(
    *,
    vehicle,
    actor,
    from_status,
    to_status,
    kind,
    title,
    payload=None,
):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=kind,
        from_status=from_status or "",
        to_status=to_status or "",
        title=title,
        payload=payload or {},
    )



def record_inspection_attachment_added(*, vehicle, item, attachment, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.ATTACHMENT_ADDED,
        title="Inspection attachment added",
        payload={
            "phase": "inspection",
            "item_id": str(item.public_id),
            "item_label": item.label,
            "attachment_id": str(attachment.public_id),
            "filename": attachment.file.name.rsplit("/", 1)[-1] if attachment.file else "",
        },
    )



def record_hammer_session_created(*, vehicle, session, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.HAMMER_STARTED,
        title="Hammer session created",
        payload={
            "hammer_session_id": str(session.public_id),
        },
    )


def record_hammer_values_updated(*, vehicle, session, actor, changed_line_ids: list[str]):
    if not changed_line_ids:
        return

    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.HAMMER_STARTED,
        title="Hammer values updated",
        payload={
            "hammer_session_id": str(session.public_id),
            "changed_line_ids": changed_line_ids,
            "est_cost_total": str(session.est_cost_total),
            "est_time_total_minutes": session.est_time_total_minutes,
        },
    )


def record_hammer_finalized(*, vehicle, session, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.HAMMER_FINALIZED,
        title="Hammer finalized",
        payload={
            "hammer_session_id": str(session.public_id),
            "est_cost_total": str(session.est_cost_total),
            "est_time_total_minutes": session.est_time_total_minutes,
        },
    )


def record_hammer_manager_assigned(*, vehicle, session, manager, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.ASSIGNED,
        title="Hammer manager assigned",
        payload={
            "hammer_session_id": str(session.public_id),
            "manager": {
                "id": str(manager.public_id),
                "email": manager.email,
                "name": manager.display_name,
            },
        },
    )


def record_buying_decision_updated(*, vehicle, decision, actor, previous_decision=None):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.BUYING_DECIDED,
        title="Buying decision updated",
        payload={
            "previous_decision": previous_decision,
            "decision": decision.decision,
            "decision_id": str(decision.public_id),
            "notes": decision.notes,
        },
    )


def record_buying_recon_seeded(*, vehicle, recon_case, actor, work_item_ids: list[str]):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.RECON_STARTED,
        title="Recon seeded from buying decision",
        payload={
            "recon_case_id": str(recon_case.public_id),
            "work_item_ids": work_item_ids,
        },
    )


def record_recon_status_updated(*, vehicle, recon_case, actor, from_status, to_status, reason=""):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=(
            HistoryEventKind.RECON_FAILED
            if to_status == "fail"
            else HistoryEventKind.RECON_COMPLETED
        ),
        from_status=from_status or "",
        to_status=vehicle.status or "",
        title="Recon status updated",
        payload={
            "recon_case_id": str(recon_case.public_id),
            "recon_status": to_status,
            "reason": reason or "",
        },
    )


def record_recon_vendor_assigned(*, vehicle, work_item, vendor_membership, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.ASSIGNED,
        title="Recon work assigned",
        payload={
            "work_item_id": str(work_item.public_id),
            "trade": {
                "id": str(work_item.trade.public_id),
                "key": work_item.trade.key,
                "label": work_item.trade.label,
            },
            "assigned_vendor_membership_id": str(vendor_membership.public_id),
            "assigned_user": {
                "id": str(vendor_membership.user.public_id),
                "email": vendor_membership.user.email,
                "name": vendor_membership.user.display_name,
            },
        },
    )

def record_vendor_work_completed(*, vehicle, work_item, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.RECON_COMPLETED,
        title="Vendor work completed",
        payload={
            "work_item_id": str(work_item.public_id),
            "trade": {
                "id": str(work_item.trade.public_id),
                "key": work_item.trade.key,
                "label": work_item.trade.label,
            },
            "actual_cost": str(work_item.actual_cost or ""),
            "actual_time_minutes": work_item.actual_time_minutes,
            "completion_date": work_item.completion_date.isoformat() if work_item.completion_date else None,
        },
    )


def record_vendor_attachment_added(*, vehicle, work_item, attachment, actor):
    HistoryEvent.objects.create(
        vehicle=vehicle,
        actor=actor,
        kind=HistoryEventKind.ATTACHMENT_ADDED,
        title="Vendor attachment added",
        payload={
            "work_item_id": str(work_item.public_id),
            "attachment_id": str(attachment.public_id),
            "kind": attachment.kind,
            "filename": attachment.file.name.rsplit("/", 1)[-1] if attachment.file else "",
        },
    )