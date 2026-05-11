"""
Tenant seeding helpers:
- Create company-scoped Trades
- Create company-level InspectionItemTemplates
- Create company/dealership VHRFieldSettings (all optional by default)

Idempotent: safe to run multiple times.
"""

from __future__ import annotations
from typing import Dict, Iterable, List, Optional, Tuple
from django.db import transaction
from accounts.models import Company, Dealership
from inspections.models import Trade, InspectionItemTemplate
from inventory.models import VHRField, VHRFieldSetting
from inspections.defaults import DEFAULT_TRADES, DEFAULT_TEMPLATES_BY_TRADE



# -------------------------
# Public entry points
# -------------------------

def seed_company_defaults(
    company: Company,
    *,
    create_vhr_settings: bool = True,
    vhr_required: bool = False,
    vhr_visible: bool = True,
    with_dealership_overrides: bool = False,
    dealerships: Optional[Iterable[Dealership]] = None,
) -> Dict[str, int]:
    """
    Seed everything for a company. Call this inside the same transaction
    that creates the Company (e.g., during signup).

    Returns a summary dict with counts created.
    """
    with transaction.atomic():
        trade_map, trade_counts = _seed_trades(company, DEFAULT_TRADES)
        tmpl_counts = _seed_templates(company, trade_map, DEFAULT_TEMPLATES_BY_TRADE)

        vhr_counts = {"vhr_settings_created": 0}
        if create_vhr_settings:
            vhr_counts["vhr_settings_created"] = _seed_vhr_settings_for_company(
                company,
                required=vhr_required,
                visible=vhr_visible,
            )

        if with_dealership_overrides and dealerships:
            _seed_dealership_overrides_for_all(company, dealerships)

    return {**trade_counts, **tmpl_counts, **vhr_counts}


def seed_dealership_overrides(
    dealership: Dealership,
    *,
    include_inactive_company_templates: bool = False,
) -> int:
    """
    Copy all company-level templates into the given dealership (idempotent),
    setting `parent` to the company template.
    """
    company = dealership.company
    # Company base templates (dealership is NULL)
    base_qs = (
        InspectionItemTemplate.objects
        .filter(company=company, dealership__isnull=True)
    )
    if not include_inactive_company_templates:
        base_qs = base_qs.filter(is_active=True)

    created = 0
    for base in base_qs.select_related("trade"):
        # Unique on (company, dealership, trade, label)
        _, was_created = InspectionItemTemplate.objects.get_or_create(
            company=company,
            dealership=dealership,
            trade=base.trade,
            label=base.label,
            defaults={
                "description": base.description,
                "is_active": base.is_active,
                "parent": base,
                "order_index": base.order_index,
            },
        )
        if was_created:
            created += 1
    return created


# -------------------------
# Internals
# -------------------------

def _seed_trades(company: Company, rows: List[dict]) -> Tuple[Dict[str, Trade], Dict[str, int]]:
    """
    Creates Trades per (company, key). If a Trade exists, optionally syncs label/desc/order.
    Returns: (key -> Trade instance, counts)
    """
    key_to_trade: Dict[str, Trade] = {}
    created = 0
    updated = 0

    for idx, row in enumerate(rows):
        key = (row.get("key") or "").strip()
        label = row.get("label") or key.replace("_", " ").title()
        description = row.get("description", "")
        order_index = row.get("order_index", (idx + 1) * 10)

        obj, was_created = Trade.objects.get_or_create(
            company=company,
            key=key,
            defaults={
                "label": label,
                "description": description,
                "order_index": order_index,
                "is_active": True,
            },
        )
        if was_created:
            created += 1
        else:
            # Bring label/desc/order up-to-date if they drifted
            fields_to_update = []
            if obj.label != label:
                obj.label = label
                fields_to_update.append("label")
            if obj.description != description:
                obj.description = description
                fields_to_update.append("description")
            if obj.order_index != order_index:
                obj.order_index = order_index
                fields_to_update.append("order_index")
            if not obj.is_active:
                obj.is_active = True
                fields_to_update.append("is_active")
            if fields_to_update:
                obj.save(update_fields=fields_to_update)
                updated += 1

        key_to_trade[key] = obj

    return key_to_trade, {"trades_created": created, "trades_updated": updated}


def _seed_templates(
    company: Company,
    trade_by_key: Dict[str, Trade],
    templates_by_trade: Dict[str, List[dict]],
) -> Dict[str, int]:
    """
    Create company-level InspectionItemTemplates (dealership=NULL) for each trade.
    Idempotent via unique (company, dealership, trade, label).
    """
    created = 0
    skipped = 0
    updated = 0

    for trade_key, items in templates_by_trade.items():
        trade = trade_by_key.get(trade_key)
        if not trade:
            # If a trade key is missing, skip its items
            skipped += len(items)
            continue

        for idx, item in enumerate(items):
            label = (item.get("label") or "").strip()
            description = item.get("description", "")
            order_index = item.get("order_index", (idx + 1) * 10)

            obj, was_created = InspectionItemTemplate.objects.get_or_create(
                company=company,
                dealership=None,
                trade=trade,
                label=label,
                defaults={
                    "description": description,
                    "order_index": order_index,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                # Keep label stable by uniqueness; update meta/order/active if needed
                fields_to_update = []
                if obj.description != description:
                    obj.description = description
                    fields_to_update.append("description")
                if obj.order_index != order_index:
                    obj.order_index = order_index
                    fields_to_update.append("order_index")
                if not obj.is_active:
                    obj.is_active = True
                    fields_to_update.append("is_active")
                if fields_to_update:
                    obj.save(update_fields=fields_to_update)
                    updated += 1

    return {"templates_created": created, "templates_updated": updated, "templates_skipped": skipped}


def _seed_vhr_settings_for_company(
    company: Company,
    *,
    required: bool = False,
    visible: bool = True,
    include_inactive_fields: bool = False,
    dealerships: Optional[Iterable[Dealership]] = None,
) -> int:
    """
    For every global VHRField, create a company-level VHRFieldSetting row
    with the given required/visible flags (defaults: all optional, visible).
    If `dealerships` is provided, also create overrides per store.
    """
    fields_qs = VHRField.objects.all()
    if not include_inactive_fields:
        fields_qs = fields_qs.filter(is_active=True)

    total_created = 0

    for field in fields_qs:
        _, created_company = VHRFieldSetting.objects.get_or_create(
            company=company,
            dealership=None,
            field=field,
            defaults={
                "required": bool(required),
                "visible": bool(visible),
                "constraints": {},
                "default_value": None,
            },
        )
        if created_company:
            total_created += 1

        if dealerships:
            for ds in dealerships:
                _, created_store = VHRFieldSetting.objects.get_or_create(
                    company=company,
                    dealership=ds,
                    field=field,
                    defaults={
                        "required": bool(required),
                        "visible": bool(visible),
                        "constraints": {},
                        "default_value": None,
                    },
                )
                if created_store:
                    total_created += 1

    return total_created


def _seed_dealership_overrides_for_all(company: Company, dealerships: Iterable[Dealership]) -> int:
    """
    Bulk helper: clone company templates to each dealership (idempotent).
    """
    created_total = 0
    for ds in dealerships:
        created_total += seed_dealership_overrides(ds)
    return created_total
