# inventory/serializers/phase.py

from rest_framework import serializers


class VehiclePhaseAdvanceSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    assign_user_id = serializers.UUIDField(required=False)