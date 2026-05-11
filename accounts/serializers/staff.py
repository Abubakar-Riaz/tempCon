# accounts/serializers/staff.py

from __future__ import annotations

from rest_framework import serializers

from accounts.models import DealershipMembership
from accounts.services.staff import serialize_permission_flags


class StaffMemberSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    user_id = serializers.UUIDField(source="user.public_id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.display_name", read_only=True)
    avatar = serializers.ImageField(source="user.avatar", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = DealershipMembership
        fields = [
            "id",
            "user_id",
            "email",
            "name",
            "avatar",
            "role",
            "is_company_owner",
            "is_default",
            "permissions",
        ]

    def get_permissions(self, obj):
        return serialize_permission_flags(obj)


class StaffRoleUpdateSerializer(serializers.Serializer):
    roles = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        required=True,
    )


class StaffPermissionUpdateSerializer(serializers.Serializer):
    allow = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    deny = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )