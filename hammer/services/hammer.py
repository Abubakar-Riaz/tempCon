# hammer/services/hammer.py

from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from hammer.models import HammerLineItem, HammerSession, HammerSessionStatus
from inspections.models import InspectionItem
from inventory.services.vehicle_history import (
    record_hammer_finalized,
    record_hammer_manager_assigned,
    record_hammer_session_created,
    record_hammer_values_updated,
)


def get_or_create_hammer_session(*, vehicle, manager=None):
    session, created = HammerSession.objects.get_or_create(
        vehicle=vehicle,
        defaults={
            "manager": manager,
            "started_at": timezone.now(),
        },
    )

    if created:
        record_hammer_session_created(
            vehicle=vehicle,
            session=session,
            actor=manager,
        )
        return session

    if manager and session.manager_id != manager.id:
        session.manager = manager
        session.save(update_fields=["manager", "updated_at"])

        record_hammer_manager_assigned(
            vehicle=vehicle,
            session=session,
            manager=manager,
            actor=manager,
        )

    return session


def upsert_hammer_values(
    *,
    session,
    lines,
    notes=None,
    calculator=None,
    finalize: bool = False,
    actor=None,
):
    if session.status == HammerSessionStatus.FINALIZED:
        raise ValueError("Finalized hammer sessions cannot be edited.")

    changed_line_ids = []

    inspection_items = {
        item.public_id: item
        for item in InspectionItem.objects.filter(
            inspection__vehicle=session.vehicle,
        ).select_related("trade")
    }

    for line in lines:
        item = inspection_items.get(line["item_id"])

        if not item:
            raise ValueError("Invalid inspection item.")

        hammer_line, _ = HammerLineItem.objects.get_or_create(
            session=session,
            inspection_item=item,
        )

        changed = False

        for field in ("est_cost", "est_time_minutes", "attributes", "notes"):
            if field not in line:
                continue

            value = line[field]

            if getattr(hammer_line, field) != value:
                setattr(hammer_line, field, value)
                changed = True

        if changed:
            hammer_line.save()
            changed_line_ids.append(str(hammer_line.public_id))

    if notes is not None:
        session.notes = notes

    if calculator is not None:
        session.derived = {
            **(session.derived or {}),
            "calculator": calculator,
        }

    totals = session.lines.aggregate(
        est_cost_total=Sum("est_cost"),
        est_time_total_minutes=Sum("est_time_minutes"),
    )

    session.est_cost_total = totals["est_cost_total"] or Decimal("0.00")
    session.est_time_total_minutes = totals["est_time_total_minutes"] or 0

    if finalize:
        session.status = HammerSessionStatus.FINALIZED
        session.completed_at = timezone.now()

    session.save()

    record_hammer_values_updated(
        vehicle=session.vehicle,
        session=session,
        actor=actor,
        changed_line_ids=changed_line_ids,
    )

    if finalize:
        record_hammer_finalized(
            vehicle=session.vehicle,
            session=session,
            actor=actor,
        )

    return session