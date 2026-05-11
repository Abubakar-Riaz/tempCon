# invites/serializers.py

from __future__ import annotations

from rest_framework import serializers

from accounts.models import DealershipRole
from invites.models import DealershipInvite


class InviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    roles = serializers.ListField(
        child=serializers.ChoiceField(choices=DealershipRole.choices),
        allow_empty=False,
    )

    def validate_roles(self, roles):
        roles = list(dict.fromkeys(roles))

        if DealershipRole.VENDOR in roles and len(roles) > 1:
            raise serializers.ValidationError("Vendor invite cannot include other roles.")

        if DealershipRole.ADMIN in roles and len(roles) > 1:
            raise serializers.ValidationError("Admin invite cannot include other roles.")

        return roles


class InviteAcceptSerializer(serializers.Serializer):
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)


class DealershipInviteSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    dealership_id = serializers.UUIDField(source="dealership.public_id", read_only=True)
    dealership_name = serializers.CharField(source="dealership.name", read_only=True)
    invited_by_name = serializers.CharField(source="invited_by.display_name", read_only=True)

    class Meta:
        model = DealershipInvite
        fields = [
            "id",
            "email",
            "role",
            "status",
            "dealership_id",
            "dealership_name",
            "invited_by_name",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "created_at",
        ]