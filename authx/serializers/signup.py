# authx/serializers/signup.py

from __future__ import annotations

from rest_framework import serializers

from accounts.models import Company, User


class SignupStartSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    company_name = serializers.CharField(max_length=200)
    terms_accepted = serializers.BooleanField(required=True)

    def validate_email(self, value):
        value = value.strip().lower()

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")

        return value

    def validate_company_name(self, value):
        value = value.strip()

        if Company.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Company name already exists.")

        return value

    def validate_terms_accepted(self, value):
        if value is not True:
            raise serializers.ValidationError("You must accept the terms and conditions.")

        return value


class SignupVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    otp_code = serializers.CharField(max_length=10)


class SignupResendSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()