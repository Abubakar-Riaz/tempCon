# authx/serializers/passwords.py

from rest_framework import serializers


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetStartSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    otp_challenge_id = serializers.UUIDField()
    otp_code = serializers.CharField(max_length=10)
    new_password = serializers.CharField(write_only=True, min_length=8)