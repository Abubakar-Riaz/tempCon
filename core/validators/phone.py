# core/validators/phone.py

from __future__ import annotations

import phonenumbers
from phonenumbers import NumberParseException
from rest_framework import serializers


def validate_e164_phone(value: str | None) -> str:
    if value in (None, ""):
        return ""

    value = str(value).strip()

    try:
        phone_number = phonenumbers.parse(value, None)
    except NumberParseException:
        raise serializers.ValidationError(
            "Enter a valid phone number with country code."
        )

    if not phonenumbers.is_valid_number(phone_number):
        raise serializers.ValidationError("Enter a valid phone number.")

    return phonenumbers.format_number(
        phone_number,
        phonenumbers.PhoneNumberFormat.E164,
    )