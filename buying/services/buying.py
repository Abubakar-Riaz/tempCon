# buying/services/buying.py

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from buying.models import BuyingDecision, BuyingDecisionStatus
from inventory.models import VehicleStatus
from inventory.services.vehicle_history import (
    record_buying_decision_updated,
    record_buying_recon_seeded,
    record_vehicle_status_changed,
)


def get_or_create_buying_decision(*, vehicle, buyer=None):
    decision, _ = BuyingDecision.objects.get_or_create(
        vehicle=vehicle,
        defaults={
            "buyer": buyer,
            "decision": BuyingDecisionStatus.PENDING,
            "decided_at": timezone.now(),
        },
    )

    if buyer and not decision.buyer_id:
        decision.buyer = buyer
        decision.save(update_fields=["buyer", "updated_at"])

    return decision


@transaction.atomic
def update_buying_decision(*, vehicle, actor, decision_value, notes=""):
    decision = get_or_create_buying_decision(
        vehicle=vehicle,
        buyer=actor,
    )

    previous_decision = decision.decision

    decision.decision = decision_value
    decision.notes = notes
    decision.buyer = actor
    decision.decided_at = timezone.now()
    decision.save(
        update_fields=[
            "decision",
            "notes",
            "buyer",
            "decided_at",
            "updated_at",
        ]
    )

    record_buying_decision_updated(
        vehicle=vehicle,
        decision=decision,
        actor=actor,
        previous_decision=previous_decision,
    )

    recon_payload = None

    if decision.decision == BuyingDecisionStatus.WIN:
        recon_payload = _move_vehicle_to_recon(vehicle=vehicle, actor=actor)

    return decision, recon_payload


def _move_vehicle_to_recon(*, vehicle, actor):
    from_status = vehicle.status

    if vehicle.status != VehicleStatus.RECON:
        vehicle.status = VehicleStatus.RECON
        vehicle.recon_at = timezone.now()
        vehicle.updated_by = actor
        vehicle.save(
            update_fields=[
                "status",
                "recon_at",
                "updated_by",
                "updated_at",
            ]
        )

        record_vehicle_status_changed(
            vehicle=vehicle,
            actor=actor,
            from_status=from_status,
            to_status=VehicleStatus.RECON,
            kind="recon_started",
            title="Vehicle moved to recon",
            payload={
                "reason": "buying_win",
            },
        )

    recon_case = _ensure_recon_case(vehicle=vehicle)
    work_item_ids = _seed_recon_work_items(vehicle=vehicle, recon_case=recon_case)

    if work_item_ids:
        record_buying_recon_seeded(
            vehicle=vehicle,
            recon_case=recon_case,
            actor=actor,
            work_item_ids=work_item_ids,
        )

    return {
        "recon_case": {
            "id": recon_case.public_id,
            "status": recon_case.status,
        },
        "created_work_item_ids": work_item_ids,
    }


def _ensure_recon_case(*, vehicle):
    from recon.models import ReconCase, ReconStatus

    recon_case, _ = ReconCase.objects.get_or_create(
        vehicle=vehicle,
        defaults={
            "status": ReconStatus.OPEN,
        },
    )

    return recon_case


def _seed_recon_work_items(*, vehicle, recon_case):
    from hammer.models import HammerLineItem
    from inspections.models import InspectionItem
    from recon.models import Priority, WorkItem

    latest_inspection = (
        vehicle.inspections
        .order_by("-started_at", "-id")
        .first()
    )

    if not latest_inspection:
        return []

    hammer_session = getattr(vehicle, "hammer_session", None)

    hammer_lines_by_item_id = {}

    if hammer_session:
        hammer_lines_by_item_id = {
            line.inspection_item_id: line
            for line in HammerLineItem.objects.filter(session=hammer_session)
        }

    existing_item_ids = set(
        WorkItem.objects
        .filter(
            recon_case=recon_case,
            source_inspection_item__isnull=False,
        )
        .values_list("source_inspection_item_id", flat=True)
    )

    created_ids = []

    items = (
        InspectionItem.objects
        .select_related("trade")
        .filter(inspection=latest_inspection)
        .exclude(id__in=existing_item_ids)
    )

    for item in items:
        hammer_line = hammer_lines_by_item_id.get(item.id)

        work_item = WorkItem.objects.create(
            recon_case=recon_case,
            trade=item.trade,
            source_inspection_item=item,
            priority=Priority.MEDIUM,
            est_cost=getattr(hammer_line, "est_cost", 0) or 0,
            est_time_minutes=getattr(hammer_line, "est_time_minutes", 0) or 0,
        )

        created_ids.append(str(work_item.public_id))

    return created_ids