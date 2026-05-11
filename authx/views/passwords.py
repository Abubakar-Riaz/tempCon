# authx/views/passwords.py

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from authx.serializers.passwords import (
    ForgotPasswordSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetStartSerializer,
)
from authx.services.passwords import (
    confirm_password_reset,
    send_password_reset_email,
    start_password_reset_otp,
)

User = get_user_model()


class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = Response(
            {"detail": "If this email exists, we sent instructions."},
            status=status.HTTP_200_OK,
        )

        try:
            user = User.objects.get(
                email__iexact=serializer.validated_data["email"],
                is_active=True,
            )
        except User.DoesNotExist:
            return response

        send_password_reset_email(request=request, user=user)
        return response


class PasswordResetStartView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            challenge = start_password_reset_otp(
                token=serializer.validated_data["token"],
                request=request,
            )
        except Exception:
            return Response(
                {"detail": "Invalid or expired reset token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "OTP sent.",
                "challenge_id": str(challenge.public_id),
                "expires_in": challenge.ttl_seconds(),
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            confirm_password_reset(**serializer.validated_data)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"detail": "Password updated. Please log in again."},
            status=status.HTTP_200_OK,
        )