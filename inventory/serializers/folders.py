# inventory/serializers/folders.py

from rest_framework import serializers


class FolderCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )

    def validate_name(self, value: str) -> str:
        value = (value or "").strip()

        if not value:
            raise serializers.ValidationError("Folder name is required.")

        return value