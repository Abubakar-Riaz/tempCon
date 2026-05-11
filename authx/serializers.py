from django.utils.text import slugify
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework import serializers

from accounts.models import Company

class SignupStartSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    email        = serializers.EmailField()
    password     = serializers.CharField(min_length=8, write_only=True, trim_whitespace=False)
    terms_accepted = serializers.BooleanField()

    # ­extra metadata reused by the view
    def validate(self, attrs):
        if not attrs["terms_accepted"]:
            raise serializers.ValidationError({"terms_accepted": ["You must accept the terms to continue."]})

        name = attrs["company_name"].strip()
        slug = slugify(name)
        if not slug:
            raise serializers.ValidationError({"company_name": ["Invalid company name."]})
        if Company.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError({"company_name": ["A company with this name already exists."]})
        if Company.objects.filter(slug=slug).exists():
            raise serializers.ValidationError({"company_name": ["Generated slug already in use. Try a different name."]})

        attrs["slug"] = slug        # cached for the view
        return attrs


class SignupVerifySerializer(serializers.Serializer):
    challenge_id      = serializers.UUIDField()
    otp_code          = serializers.CharField(min_length=4, max_length=10)
    refresh_transport = serializers.ChoiceField(
        choices=[("cookie", "cookie"), ("body", "body")],
        required=False,
        default="cookie",
    )


class SignupResendSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()



class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    refresh_transport = serializers.ChoiceField(
        choices=[("cookie", "cookie"), ("body", "body")],
        required=False,
    )

    def validate(self, attrs):
        user = authenticate(username=attrs["email"].lower().strip(), password=attrs["password"])
        if not user or not user.is_active:
            raise serializers.ValidationError({"non_field_errors": ["Invalid credentials."]})
        attrs["user"] = user
        return attrs


class OtpVerifySerializer(serializers.Serializer):
    challenge_id      = serializers.UUIDField()
    otp_code          = serializers.CharField(min_length=4, max_length=10)
    refresh_transport = serializers.ChoiceField(
        choices=[("cookie", "cookie"), ("body", "body")],
        required=False,
        default="cookie",
    )


class OtpResendSerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()


# --------------------  PASSWORD  --------------------


class ForgotPasswordStartSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordVerifySerializer(serializers.Serializer):
    challenge_id  = serializers.UUIDField()
    otp_code      = serializers.CharField(min_length=4, max_length=10)
    new_password  = serializers.CharField(min_length=8, max_length=128, write_only=True)


class ChangePasswordStartSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, max_length=128, write_only=True)

    def validate(self, attrs):
        request = self.context["request"]
        user    = request.user
        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"non_field_errors": ["Authentication required."]})
        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError({"old_password": ["Incorrect password."]})
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError({"new_password": ["New password must be different from the old password."]})
        return attrs


class ChangePasswordVerifySerializer(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    otp_code     = serializers.CharField(min_length=4, max_length=10)