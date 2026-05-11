# authx/serializers/sessions.py

from __future__ import annotations

from rest_framework import serializers


class ActiveSessionSerializer(serializers.Serializer):
    id = serializers.CharField()
    device = serializers.CharField()
    browser = serializers.CharField()
    location = serializers.CharField()
    ip = serializers.CharField(allow_null=True, required=False)
    last_active_date = serializers.DateField()
    last_active_time = serializers.TimeField()
    is_current = serializers.BooleanField()


class SessionRevokeSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()


class LoginHistorySerializer(serializers.Serializer):
    id = serializers.CharField()
    date = serializers.DateField()
    time = serializers.TimeField()
    device = serializers.CharField()
    browser = serializers.CharField()
    location = serializers.CharField()
    status = serializers.CharField()
    method = serializers.CharField()