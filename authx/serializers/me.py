# authx/serializers/me.py

from __future__ import annotations

from rest_framework import serializers

from accounts.models import Company, Dealership, DealershipMembership, User


class UserPublicSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    name = serializers.CharField(source="display_name", read_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "first_name",
            "last_name",
            "avatar_url",
            "timezone",
            "language",
            "date_format",
            "hour_format",
            "week_start",
            "is_email_verified",
        ]

    def get_avatar_url(self, obj):
        request = self.context.get("request")

        if not getattr(obj, "avatar", None):
            return ""

        url = obj.avatar.url
        return request.build_absolute_uri(url) if request else url


class CompanyPublicSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
        ]


class DealershipPublicSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Dealership
        fields = [
            "id",
            "name",
            "slug",
            "is_active",
            "is_default",
            "is_pinned",
        ]


class MembershipPublicSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = DealershipMembership
        fields = [
            "id",
            "role",
            "status",
            "is_company_owner",
            "is_default",
            "joined_at",
        ]


class MeSerializer(serializers.Serializer):
    user = UserPublicSerializer()
    company = CompanyPublicSerializer(allow_null=True)
    dealership = DealershipPublicSerializer(allow_null=True)
    membership = MembershipPublicSerializer(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())
    features = serializers.DictField()
    limits = serializers.DictField()
    detail = serializers.CharField(required=False)