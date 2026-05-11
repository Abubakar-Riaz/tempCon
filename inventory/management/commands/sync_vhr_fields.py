from __future__ import annotations

import importlib
from typing import Iterable, List, Dict, Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import VHRField

DEFAULT_MODULE = "inspections.vhr_fields_catalog"
DEFAULT_ATTR = "VHR_FIELD_CATALOG_SUGGESTED"


class Command(BaseCommand):
    help = (
        "Create or update global VHRField rows from a Python catalog.\n"
        "By default reads inspections.vhr_fields_catalog:VHR_FIELD_CATALOG_SUGGESTED"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--module",
            default=DEFAULT_MODULE,
            help=f"Python module path to import (default: {DEFAULT_MODULE})",
        )
        parser.add_argument(
            "--attr",
            default=DEFAULT_ATTR,
            help=f"Attribute name on module that contains the list (default: {DEFAULT_ATTR})",
        )
        parser.add_argument(
            "--only",
            nargs="*",
            help="Limit to specific field keys (space-separated).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would happen without writing changes.",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update label/group/help_text/options/order_index/is_active if they differ.",
        )
        parser.add_argument(
            "--allow-type-change",
            action="store_true",
            help="Also update data_type if it differs (DANGEROUS if data already exists).",
        )
        parser.add_argument(
            "--start-order",
            type=int,
            default=10,
            help="Order index to start from if not provided in the catalog (default: 10).",
        )
        parser.add_argument(
            "--step",
            type=int,
            default=10,
            help="Order index step if not provided in the catalog (default: 10).",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Set is_active=False for fields present in DB but NOT in the provided catalog/selection.",
        )

    def handle(self, *args, **opts):
        module_path = opts["module"]
        attr_name = opts["attr"]
        only_keys: Optional[Iterable[str]] = set(k.strip() for k in opts["only"]) if opts["only"] else None
        dry_run: bool = bool(opts["dry_run"])
        do_update: bool = bool(opts["update"])
        allow_type_change: bool = bool(opts["allow_type_change"])
        start_order: int = int(opts["start_order"])
        step: int = int(opts["step"])
        deactivate_missing: bool = bool(opts["deactivate_missing"])

        try:
            mod = importlib.import_module(module_path)
        except Exception as e:
            raise CommandError(f"Could not import module {module_path}: {e}")

        if not hasattr(mod, attr_name):
            raise CommandError(f"Module {module_path} has no attribute {attr_name}")

        catalog: List[Dict[str, Any]] = getattr(mod, attr_name)
        if not isinstance(catalog, list):
            raise CommandError(f"{module_path}:{attr_name} must be a list of dicts")

        # Filter catalog if --only was provided
        if only_keys:
            catalog = [row for row in catalog if row.get("key") in only_keys]

        # Validate unique keys
        keys = [row.get("key") for row in catalog]
        if len(keys) != len(set(keys)):
            raise CommandError("Duplicate keys found in catalog selection.")

        self.stdout.write(self.style.NOTICE(f"Loaded {len(catalog)} field(s) from {module_path}:{attr_name}"))

        created = 0
        updated = 0

        @transaction.atomic
        def _apply():
            nonlocal created, updated

            # Build set of target keys (for optional deactivation step)
            target_keys = set(keys)

            # Create/update from catalog
            for idx, row in enumerate(catalog):
                key = (row.get("key") or "").strip()
                if not key:
                    raise CommandError(f"Row #{idx} missing 'key'.")

                # Defaults / normalization
                label = row.get("label") or key.replace("_", " ").title()
                data_type = (row.get("data_type") or "").strip().upper()
                group = row.get("group", "") or ""
                help_text = row.get("help_text", "") or ""
                options = row.get("options", {}) or {}
                order_index = row.get("order_index", start_order + step * idx)
                is_active = bool(row.get("is_active", True))

                obj, was_created = VHRField.objects.get_or_create(
                    key=key,
                    defaults=dict(
                        label=label,
                        data_type=data_type,
                        group=group,
                        help_text=help_text,
                        options=options,
                        order_index=order_index,
                        is_active=is_active,
                    ),
                )
                if was_created:
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"[CREATE] {key} → {label} ({data_type})"))
                    continue

                # Optionally update changed fields
                if do_update:
                    fields_to_update = []

                    if obj.label != label:
                        obj.label = label
                        fields_to_update.append("label")
                    if obj.group != group:
                        obj.group = group
                        fields_to_update.append("group")
                    if obj.help_text != help_text:
                        obj.help_text = help_text
                        fields_to_update.append("help_text")
                    if obj.options != options:
                        obj.options = options
                        fields_to_update.append("options")
                    if obj.order_index != order_index:
                        obj.order_index = order_index
                        fields_to_update.append("order_index")
                    if obj.is_active != is_active:
                        obj.is_active = is_active
                        fields_to_update.append("is_active")

                    if allow_type_change and obj.data_type != data_type:
                        obj.data_type = data_type
                        fields_to_update.append("data_type")

                    if fields_to_update:
                        obj.save(update_fields=fields_to_update)
                        updated += 1
                        self.stdout.write(self.style.WARNING(f"[UPDATE] {key} fields: {', '.join(fields_to_update)}"))

            # Optionally deactivate DB fields not present in the catalog selection
            if deactivate_missing:
                db_keys = set(VHRField.objects.values_list("key", flat=True))
                missing = db_keys - target_keys if target_keys else set()
                if missing:
                    for key in sorted(missing):
                        obj = VHRField.objects.filter(key=key, is_active=True).first()
                        if obj:
                            obj.is_active = False
                            obj.save(update_fields=["is_active"])
                            self.stdout.write(self.style.WARNING(f"[DEACTIVATE] {key}"))
                else:
                    self.stdout.write(self.style.NOTICE("No extra fields to deactivate."))

        if dry_run:
            self.stdout.write(self.style.HTTP_INFO("Dry-run mode: no changes will be written."))
            # Wrap in atomic and then force rollback by raising
            try:
                _apply()
                raise RuntimeError("Dry-run complete; simulated changes rolled back.")
            except RuntimeError as e:
                self.stdout.write(self.style.NOTICE(str(e)))
        else:
            _apply()

        self.stdout.write(self.style.SUCCESS(f"Done. created={created}, updated={updated}"))
