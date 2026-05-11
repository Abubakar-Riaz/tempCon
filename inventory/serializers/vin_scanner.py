from __future__ import annotations
from rest_framework import serializers
from inventory.services.vehicle_helpers import _validate_vin



class VinSearchQuerySerializer(serializers.Serializer):
    vin = serializers.CharField(required=True, allow_blank=False)

    def validate_vin(self, value):
        return _validate_vin(value)


class VinQuickAddSerializer(serializers.Serializer):
    vin = serializers.CharField(required=True, allow_blank=False)
    vehicle = serializers.DictField(required=False)

    def validate_vin(self, value):
        return _validate_vin(value)