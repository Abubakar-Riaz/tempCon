# authx/serializers/login.py

from __future__ import annotations

from django.contrib.auth import authenticate
from rest_framework import serializers

from accounts.models import User
from authx.models import AuthProvider
from authx.services.providers import has_provider


LOGIN_MISMATCH_MSG = (
    "We couldn’t sign you in with that method. "
    "Try a different sign-in option, or use a different email."
)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get("request")

        email = attrs["email"].strip().lower()
        password = attrs["password"]

        user = authenticate(request, username=email, password=password)

        if not user:
            raise serializers.ValidationError({"detail": LOGIN_MISMATCH_MSG})

        if not user.is_active:
            raise serializers.ValidationError({"detail": LOGIN_MISMATCH_MSG})

        if not getattr(user, "is_email_verified", False):
            raise serializers.ValidationError(
                {"detail": "Please verify your email before logging in."}
            )

        if not has_provider(user, AuthProvider.PASSWORD):
            raise serializers.ValidationError({"detail": LOGIN_MISMATCH_MSG})

        attrs["user"] = user
        attrs["email"] = email
        return attrs


class LoginOtpVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    otp_code = serializers.CharField(max_length=10)


class LoginOtpResendSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()


class UserPublicSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    name = serializers.CharField(source="display_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "first_name",
            "last_name",
            "avatar",
            "timezone",
            "language",
            "date_format",
            "hour_format",
            "week_start",
        ]