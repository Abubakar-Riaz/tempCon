# invites/views.py

from __future__ import annotations

from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.request_context import _get_access_context
from invites.models import DealershipInvite
from invites.serializers import (
    DealershipInviteSerializer,
    InviteAcceptSerializer,
    InviteCreateSerializer,
)
from invites.services import (
    accept_invite,
    create_invite,
    get_invite_or_404,
    get_invites_queryset,
    resend_invite,
    revoke_invite,
)


class InviteListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_ctx, ctx = _get_access_context(request)

        qs = get_invites_queryset(ctx)

        status_filter = (request.query_params.get("status") or "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)

        return Response(
            {
                "count": qs.count(),
                "results": DealershipInviteSerializer(qs, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        raw_ctx, ctx = _get_access_context(request)

        serializer = InviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite = create_invite(
            ctx=ctx,
            email=serializer.validated_data["email"],
            roles=serializer.validated_data["roles"],
        )

        return Response(
            DealershipInviteSerializer(invite).data,
            status=status.HTTP_201_CREATED,
        )


class InviteResendView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invite_id):
        raw_ctx, ctx = _get_access_context(request)

        invite = get_invite_or_404(ctx=ctx, invite_public_id=invite_id)
        invite = resend_invite(ctx=ctx, invite=invite)

        return Response(
            DealershipInviteSerializer(invite).data,
            status=status.HTTP_200_OK,
        )


class InviteRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invite_id):
        raw_ctx, ctx = _get_access_context(request)

        invite = get_invite_or_404(ctx=ctx, invite_public_id=invite_id)
        invite = revoke_invite(ctx=ctx, invite=invite)

        return Response(
            DealershipInviteSerializer(invite).data,
            status=status.HTTP_200_OK,
        )


class InviteAcceptView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        serializer = InviteAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite, membership, created_user = accept_invite(
            token=token,
            password=serializer.validated_data.get("password", ""),
        )

        return Response(
            {
                "accepted": True,
                "created_user": created_user,
                "invite": DealershipInviteSerializer(invite).data,
                "membership_id": str(membership.public_id),
            },
            status=status.HTTP_200_OK,
        )