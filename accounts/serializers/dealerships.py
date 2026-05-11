# accounts/serializers/dealerships.py

from __future__ import annotations

from rest_framework import serializers

from accounts.models import Dealership
from core.validators.phone import validate_e164_phone


class DealershipListQuerySerializer(serializers.Serializer):
    page = serializers.IntegerField(required=False, min_value=1, default=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100, default=50)


class DealershipSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Dealership
        fields = [
            "id",
            "name",
            "legal_name",
            "slug",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_active",
            "is_default",
            "is_pinned",
        ]


class DealershipCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)

    def validate_name(self, value):
        value = value.strip()
        company = self.context["company"]

        if Dealership.objects.filter(company=company, name__iexact=value).exists():
            raise serializers.ValidationError("Dealership name already exists.")

        return value


class DealershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dealership
        fields = [
            "name",
            "legal_name",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "postal_code",
            "country",
            "is_active",
            "is_default",
            "is_pinned",
        ]

    def validate_phone(self, value):
        return validate_e164_phone(value)

    def validate_name(self, value):
        value = value.strip()
        dealership = self.instance

        if (
            Dealership.objects
            .filter(company=dealership.company, name__iexact=value)
            .exclude(pk=dealership.pk)
            .exists()
        ):
            raise serializers.ValidationError("Dealership name already exists.")

        return value