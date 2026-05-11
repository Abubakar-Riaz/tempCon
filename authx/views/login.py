# authx/views/login.py

from __future__ import annotations

from django.contrib.auth import login as django_login, logout as django_logout
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authx.models import LoginMethod, LoginStatus, OTPChallenge, OTPPurpose
from authx.serializers.login import (
    LoginOtpResendSerializer,
    LoginOtpVerifySerializer,
    LoginSerializer,
    UserPublicSerializer,
)
from authx.services.login_events import log_login_event
from authx.services.sessions import (
    ensure_device_id,
    is_known_device,
    issue_tokens_and_session,
    set_device_cookie,
)
from authx.utils.otp import (
    create_login_challenge,
    resend_login_challenge,
    verify_login_challenge,
)
from authx.utils.tokens import (
    get_refresh_from_request,
    mint_rotated_tokens_from_raw,
    set_auth_cookies,
)


class LoginStartView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )

        device_id, created_new_device = ensure_device_id(request)

        if not serializer.is_valid():
            email = (request.data.get("email") or "").strip().lower()

            log_login_event(
                user=None,
                email=email,
                status=LoginStatus.FAILED,
                method=LoginMethod.PASSWORD,
                request=request,
                device_id=device_id,
                failure_reason="invalid_credentials",
            )

            return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data["user"]

        if is_known_device(user, device_id):
            access, refresh, session = issue_tokens_and_session(
                user=user,
                request=request,
                device_id=device_id,
            )

            django_login(request._request, user)

            log_login_event(
                user=user,
                email=user.email,
                status=LoginStatus.SUCCESS,
                method=LoginMethod.PASSWORD,
                request=request,
                device_id=device_id,
            )

            response = Response(
                {
                    "detail": "Logged in.",
                    "session_id": str(session.public_id),
                    "user": UserPublicSerializer(user).data,
                },
                status=status.HTTP_200_OK,
            )

            if created_new_device:
                set_device_cookie(response, device_id)

            set_auth_cookies(response, access=access, refresh=refresh)
            return response

        OTPChallenge.objects.filter(
            user=user,
            email=user.email.lower(),
            purpose=OTPPurpose.LOGIN_NEW_DEVICE,
            device_id=device_id,
            consumed_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).update(consumed_at=timezone.now())

        challenge = create_login_challenge(
            user=user,
            request=request,
            device_id=device_id,
        )

        log_login_event(
            user=user,
            email=user.email,
            status=LoginStatus.FAILED,
            method=LoginMethod.PASSWORD,
            request=request,
            device_id=device_id,
            failure_reason="new_device_otp_required",
        )

        mask = f"{user.email[0]}***@{user.email.split('@', 1)[1]}"

        response = Response(
            {
                "detail": "OTP required for new device.",
                "requires_otp": True,
                "challenge_id": str(challenge.public_id),
                "mask": mask,
                "expires_in": challenge.ttl_seconds(),
            },
            status=status.HTTP_200_OK,
        )

        if created_new_device:
            set_device_cookie(response, device_id)

        return response


class LoginVerifyOtpView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginOtpVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge_id = serializer.validated_data["challenge_id"]
        otp_code = serializer.validated_data["otp_code"]

        try:
            challenge = OTPChallenge.objects.select_related("user").get(
                public_id=challenge_id,
                purpose=OTPPurpose.LOGIN_NEW_DEVICE,
            )
        except OTPChallenge.DoesNotExist:
            return Response(
                {"detail": "Invalid OTP challenge."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            challenge = verify_login_challenge(challenge.public_id, otp_code)
        except ValueError as exc:
            log_login_event(
                user=challenge.user,
                email=challenge.email,
                status=LoginStatus.FAILED,
                method=LoginMethod.OTP,
                request=request,
                device_id=challenge.device_id,
                failure_reason=str(exc),
            )

            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = challenge.user

        if not user:
            return Response(
                {"detail": "Invalid challenge user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_id = challenge.device_id
        access, refresh, session = issue_tokens_and_session(
            user=user,
            request=request,
            device_id=device_id,
        )

        django_login(request._request, user)

        log_login_event(
            user=user,
            email=user.email,
            status=LoginStatus.SUCCESS,
            method=LoginMethod.OTP,
            request=request,
            device_id=device_id,
        )

        response = Response(
            {
                "detail": "Logged in.",
                "session_id": str(session.public_id),
                "user": UserPublicSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

        set_device_cookie(response, device_id)
        set_auth_cookies(response, access=access, refresh=refresh)
        return response


class LoginResendOtpView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginOtpResendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            challenge = resend_login_challenge(
                serializer.validated_data["challenge_id"]
            )
        except TimeoutError:
            return Response(
                {"detail": "Please wait before requesting another code."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except ValueError:
            return Response(
                {"detail": "Challenge invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "sent": True,
                "challenge_id": str(challenge.public_id),
                "expires_in": challenge.ttl_seconds(),
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = get_refresh_from_request(request)

        if not refresh_token:
            return Response(
                {"detail": "Missing refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            access, refresh = mint_rotated_tokens_from_raw(refresh_token)
        except Exception:
            return Response(
                {"detail": "Invalid refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response(
            {"detail": "Token refreshed."},
            status=status.HTTP_200_OK,
        )
        set_auth_cookies(response, access=access, refresh=refresh)
        return response


