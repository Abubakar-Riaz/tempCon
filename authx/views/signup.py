# authx/views/signup.py

from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authx.serializers.signup import (
    SignupResendSerializer,
    SignupStartSerializer,
    SignupVerifySerializer,
)
from authx.services.signup import complete_signup_from_challenge
from authx.utils.otp import (
    create_signup_challenge,
    resend_signup_challenge,
    verify_signup_challenge,
)


class SignupStartView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        company_name = serializer.validated_data["company_name"]

        challenge = create_signup_challenge(
            email,
            company_name=company_name,
            request=request,
            set_password=password,
        )

        mask = f"{email[0]}***@{email.split('@', 1)[1]}"

        return Response(
            {
                "requires_otp": True,
                "challenge_id": str(challenge.public_id),
                "mask": mask,
                "expires_in": challenge.ttl_seconds(),
            },
            status=status.HTTP_200_OK,
        )


class SignupVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge = verify_signup_challenge(
            serializer.validated_data["challenge_id"],
            serializer.validated_data["otp_code"],
        )

        user, company, dealership, membership = complete_signup_from_challenge(
            challenge=challenge,
        )

        return Response(
            {
                "signup_complete": True,
                "login_required": True,
                "user_id": str(user.public_id),
                "company_id": str(company.public_id),
                "dealership_id": str(dealership.public_id),
                "membership_id": str(membership.public_id),
                "billing_setup_required": True,
            },
            status=status.HTTP_200_OK,
        )


class SignupResendOtpView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge = resend_signup_challenge(
            serializer.validated_data["challenge_id"]
        )

        return Response(
            {
                "sent": True,
                "challenge_id": str(challenge.public_id),
                "expires_in": challenge.ttl_seconds(),
            },
            status=status.HTTP_200_OK,
        )