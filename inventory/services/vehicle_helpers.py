# inventory/services/vehicle_helpers.py

from __future__ import annotations

from datetime import datetime
from datetime import timezone as py_timezone

from django.core.exceptions import ValidationError
from django.utils import timezone


def _normalize_vin(vin: str) -> str:
    return (vin or "").strip().upper()


def _validate_vin(vin: str) -> str:
    vin = _normalize_vin(vin)

    if len(vin) != 17:
        raise ValidationError("VIN must be exactly 17 characters.")

    invalid_chars = {"I", "O", "Q"}

    if any(char in invalid_chars for char in vin):
        raise ValidationError("VIN contains invalid characters.")

    return vin


def _parse_start_time(value: str):
    if not value:
        return None

    value = value.strip()

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(
            parsed,
            timezone.get_current_timezone(),
        )

    return parsed.astimezone(py_timezone.utc)