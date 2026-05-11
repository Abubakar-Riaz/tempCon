# authx/views/google.py

from __future__ import annotations

from django.contrib.auth import get_user_model, login as django_login
from django.db import transaction

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import MembershipStatus
from authx.models import LoginMethod, LoginStatus
from authx.serializers.login import UserPublicSerializer
from authx.services.bootstrap import bootstrap_account_for_user
from authx.services.google import ensure_google_provider, verify_google_id_token
from authx.services.login_events import log_login_event
from authx.services.sessions import (
    ensure_device_id,
    issue_tokens_and_session,
    set_device_cookie,
)
from authx.utils.tokens import set_auth_cookies

User = get_user_model()


class GoogleAuthView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        device_id, created_new_device = ensure_device_id(request)
        id_token = (request.data.get("id_token") or "").strip()

        if not id_token:
            log_login_event(
                user=None,
                email="",
                status=LoginStatus.FAILED,
                method=LoginMethod.GOOGLE,
                request=request,
                device_id=device_id,
                failure_reason="missing_id_token",
            )
            return Response(
                {"detail": "Missing id_token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = verify_google_id_token(id_token)
        except Exception:
            log_login_event(
                user=None,
                email="",
                status=LoginStatus.FAILED,
                method=LoginMethod.GOOGLE,
                request=request,
                device_id=device_id,
                failure_reason="invalid_google_token",
            )
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = (payload.get("email") or "").strip().lower()
        full_name = (payload.get("name") or "").strip()
        provider_uid = (payload.get("sub") or "").strip()

        if not email or not provider_uid:
            log_login_event(
                user=None,
                email=email,
                status=LoginStatus.FAILED,
                method=LoginMethod.GOOGLE,
                request=request,
                device_id=device_id,
                failure_reason="missing_google_claims",
            )
            return Response(
                {"detail": "Invalid Google token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "full_name": full_name,
                    "is_active": True,
                    "is_email_verified": True,
                },
            )

            update_fields = []

            if full_name and not user.full_name:
                user.full_name = full_name
                update_fields.append("full_name")

            if not user.is_active:
                user.is_active = True
                update_fields.append("is_active")

            if not user.is_email_verified:
                user.is_email_verified = True
                update_fields.append("is_email_verified")

            if update_fields:
                user.save(update_fields=update_fields)

            ensure_google_provider(user, provider_uid)

            has_membership = user.dealership_memberships.filter(
                status=MembershipStatus.ACTIVE,
                dealership__is_active=True,
                company__is_active=True,
            ).exists()

            if created or not has_membership:
                bootstrap_account_for_user(
                    user=user,
                    company_name=full_name or email.split("@")[0],
                )

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
            method=LoginMethod.GOOGLE,
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