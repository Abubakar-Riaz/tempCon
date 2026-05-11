# notifications/serializers.py

from rest_framework import serializers

from notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    actor = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "category",
            "priority",
            "title",
            "body",
            "entity_type",
            "entity_public_id",
            "target_url",
            "is_read",
            "read_at",
            "metadata",
            "actor",
            "created_at",
            "updated_at",
        ]

    def get_actor(self, obj):
        if not obj.actor_id:
            return None

        return {
            "id": obj.actor.public_id,
            "email": obj.actor.email,
            "display_name": obj.actor.display_name,
        }


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "in_app_enabled",
            "websocket_enabled",
            "email_enabled",
            "email_important_only",
            "category_preferences",
            "type_preferences",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]