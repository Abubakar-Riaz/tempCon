# inventory/serializers/vehicles.py

from __future__ import annotations

from datetime import timezone as py_timezone
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from rest_framework import serializers

from inventory.models import HistoryEvent, Vehicle, VehicleStatus
from inventory.services.vehicle_helpers import (
    _normalize_vin,
    _parse_start_time,
    _validate_vin,
)

VALID_STATUSES = {value for value, _ in VehicleStatus.choices}


class VehicleListItemSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    updated_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "vin",
            "stock_no",
            "year",
            "make",
            "model",
            "trim",
            "main_description",
            "exterior_color",
            "status",
            "source",
            "created_at",
            "updated_at",
            "updated_by_email",
        )

    def get_updated_by_email(self, obj):
        return obj.updated_by.email if obj.updated_by else None


class VehicleCreateUpdateSerializer(serializers.ModelSerializer):
    vin = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Vehicle
        fields = (
            "vin",
            "stock_no",
            "year",
            "make",
            "model",
            "trim",
            "run_number",
            "auction_house",
            "auction_sale_lane",
            "auction_start_at",
            "main_description",
            "secondary_description",
            "title_status",
            "condition_grade",
            "mmr",
            "mileage",
            "engine",
            "transmission",
            "exterior_color",
            "interior_color",
            "consignor_name",
            "consignor_email",
            "consignor_address",
            "auction_notes",
            "status",
        )

    def validate_vin(self, value):
        return _validate_vin(value)

    def validate_status(self, value):
        if value in (None, ""):
            return value

        if value not in VALID_STATUSES:
            raise serializers.ValidationError(
                f"Invalid status. Valid: {', '.join(sorted(VALID_STATUSES))}."
            )

        return value

    def validate_condition_grade(self, value):
        if value in (None, ""):
            return None

        try:
            value = Decimal(str(value))
        except InvalidOperation:
            raise serializers.ValidationError("Invalid decimal.")

        if value.as_tuple().exponent < -1:
            raise serializers.ValidationError("Condition grade may have at most 1 decimal place.")

        if value < Decimal("0.0") or value > Decimal("5.0"):
            raise serializers.ValidationError("Condition grade must be between 0.0 and 5.0.")

        return value

    def validate_mmr(self, value):
        if value in (None, ""):
            return None

        value = int(value)

        if value < 0:
            raise serializers.ValidationError("MMR must be non-negative.")

        return value

    def validate_mileage(self, value):
        if value in (None, ""):
            return None

        value = int(value)

        if value < 0:
            raise serializers.ValidationError("Mileage must be non-negative.")

        return value

    def validate_auction_start_at(self, value):
        if value in (None, ""):
            return None

        if isinstance(value, str):
            parsed = _parse_start_time(value)

            if not parsed:
                raise serializers.ValidationError("Invalid start time.")

            return parsed

        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())

        return value.astimezone(py_timezone.utc)

    def validate(self, attrs):
        company = self.context.get("company")
        instance = self.instance

        vin = _normalize_vin(attrs.get("vin") or (instance.vin if instance else ""))

        if instance and "vin" in attrs and vin != instance.vin:
            raise serializers.ValidationError({"vin": ["VIN cannot be changed."]})

        qs = Vehicle.objects.filter(company=company, vin=vin)

        if instance:
            qs = qs.exclude(pk=instance.pk)

        if qs.exists():
            raise serializers.ValidationError({"vin": ["A vehicle with this VIN already exists."]})

        attrs["vin"] = vin
        return attrs


class VehicleDetailSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    dealership = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = (
            "id",
            "vin",
            "stock_no",
            "year",
            "make",
            "model",
            "trim",
            "run_number",
            "auction_house",
            "auction_sale_lane",
            "auction_start_at",
            "main_description",
            "secondary_description",
            "title_status",
            "condition_grade",
            "mmr",
            "mileage",
            "engine",
            "transmission",
            "exterior_color",
            "interior_color",
            "consignor_name",
            "consignor_email",
            "consignor_address",
            "auction_notes",
            "source",
            "status",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "dealership",
            "permissions",
        )

    def get_dealership(self, obj):
        return {
            "id": obj.dealership.public_id,
            "name": obj.dealership.name,
        }

    def get_created_by(self, obj):
        if not obj.created_by:
            return None

        return {
            "id": obj.created_by.public_id,
            "email": obj.created_by.email,
            "name": obj.created_by.display_name,
        }

    def get_updated_by(self, obj):
        if not obj.updated_by:
            return None

        return {
            "id": obj.updated_by.public_id,
            "email": obj.updated_by.email,
            "name": obj.updated_by.display_name,
        }

    def get_permissions(self, obj):
        return self.context.get("permissions", {})


class VehicleHistoryEventSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    actor = serializers.SerializerMethodField()

    class Meta:
        model = HistoryEvent
        fields = (
            "id",
            "kind",
            "from_status",
            "to_status",
            "title",
            "description",
            "payload",
            "actor",
            "occurred_at",
            "created_at",
        )

    def get_actor(self, obj):
        if not obj.actor:
            return None

        return {
            "id": obj.actor.public_id,
            "email": obj.actor.email,
            "name": obj.actor.display_name,
        }