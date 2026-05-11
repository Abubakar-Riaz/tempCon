# inventory/serializers/vhr.py

from __future__ import annotations

from typing import Any

from django.utils import timezone
from rest_framework import serializers

from inventory.models import (
    VHRField,
    VHRFieldSetting,
    VHRFieldType,
    VehicleHistoryReport,
)
from inventory.services.vehicle_helpers import _parse_start_time


class VHRUpdateSerializer(serializers.Serializer):
    data = serializers.DictField(required=True)

    def validate_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Must be an object.")
        return value


class VehicleHistoryReportSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = VehicleHistoryReport
        fields = (
            "id",
            "data",
            "required_config_snapshot",
            "created_at",
            "updated_at",
        )


def get_effective_vhr_config(*, company, dealership) -> list[dict[str, Any]]:
    fields = VHRField.objects.filter(is_active=True).order_by("order_index", "label")

    company_settings = {
        item.field_id: item
        for item in VHRFieldSetting.objects.filter(
            company=company,
            dealership__isnull=True,
        )
    }

    dealership_settings = {
        item.field_id: item
        for item in VHRFieldSetting.objects.filter(
            company=company,
            dealership=dealership,
        )
    }

    result = []

    for field in fields:
        setting = dealership_settings.get(field.id) or company_settings.get(field.id)

        visible = getattr(setting, "visible", True) if setting else True
        if not visible:
            continue

        required = getattr(setting, "required", False) if setting else False
        constraints = getattr(setting, "constraints", {}) if setting else {}
        default_value = getattr(setting, "default_value", None) if setting else None

        options = {
            **(field.options or {}),
            **(constraints or {}),
        }

        result.append(
            {
                "id": field.public_id,
                "key": field.key,
                "label": field.label,
                "data_type": field.data_type,
                "group": field.group or "",
                "help_text": field.help_text or "",
                "required": required,
                "options": options,
                "default_value": default_value,
            }
        )

    return result


def build_vhr_payload(*, vehicle, company, dealership) -> dict:
    config = get_effective_vhr_config(
        company=company,
        dealership=dealership,
    )

    report = getattr(vehicle, "vhr", None)
    saved_data = report.data if report else {}

    grouped = {}

    for field in config:
        group = field["group"]
        grouped.setdefault(group, [])

        grouped[group].append(
            {
                "key": field["key"],
                "label": field["label"],
                "data_type": field["data_type"],
                "help_text": field["help_text"],
                "required": field["required"],
                "options": field["options"],
                "value": saved_data.get(field["key"], field["default_value"]),
            }
        )

    return {
        "vehicle": {
            "id": vehicle.public_id,
            "vin": vehicle.vin,
            "status": vehicle.status,
            "vhr_at": vehicle.vhr_at,
        },
        "groups": [
            {
                "group": group,
                "fields": fields,
            }
            for group, fields in grouped.items()
        ],
    }


def coerce_vhr_value(*, field: dict, value):
    if value is None:
        return None

    data_type = field["data_type"]
    options = field.get("options") or {}

    if data_type == VHRFieldType.TEXT:
        value = str(value)
        return value if options.get("preserve_whitespace") else value.strip()

    if data_type == VHRFieldType.NUMBER:
        value = float(value)
        minimum = options.get("min")
        maximum = options.get("max")

        if minimum is not None and value < float(minimum):
            raise serializers.ValidationError(f"Must be >= {minimum}.")

        if maximum is not None and value > float(maximum):
            raise serializers.ValidationError(f"Must be <= {maximum}.")

        return int(value) if value.is_integer() else value

    if data_type == VHRFieldType.BOOL:
        if isinstance(value, bool):
            return value

        value = str(value).strip().lower()

        if value in {"true", "1", "yes", "y"}:
            return True

        if value in {"false", "0", "no", "n"}:
            return False

        raise serializers.ValidationError("Must be true or false.")

    if data_type == VHRFieldType.DATE:
        parsed = _parse_start_time(value)

        if not parsed:
            raise serializers.ValidationError("Invalid date.")

        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

        return parsed.isoformat()

    if data_type == VHRFieldType.ENUM:
        choices = options.get("choices") or []
        allowed = {
            str(choice.get("value"))
            for choice in choices
            if isinstance(choice, dict)
        }

        value = str(value)

        if value not in allowed:
            raise serializers.ValidationError("Invalid choice.")

        return value

    return value


def build_required_snapshot(config: list[dict]) -> dict:
    return {
        field["key"]: {
            "visible": True,
            "required": field["required"],
        }
        for field in config
    }