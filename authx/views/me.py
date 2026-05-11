# authx/views/me.py

from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from authx.serializers.me import MeSerializer, UserPublicSerializer
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            raw_ctx = resolve_request_dealership_context(request)
        except Exception as exc:
            return Response(
                {
                    "user": UserPublicSerializer(
                        request.user,
                        context={"request": request},
                    ).data,
                    "company": None,
                    "dealership": None,
                    "membership": None,
                    "permissions": [],
                    "features": {},
                    "limits": {},
                    "detail": str(exc),
                },
                status=status.HTTP_200_OK,
            )

        ctx = build_access_context(
            user=raw_ctx.user,
            membership=raw_ctx.membership,
            dealership=raw_ctx.dealership,
            subscription=raw_ctx.subscription,
        )

        payload = {
            "user": raw_ctx.user,
            "company": raw_ctx.company,
            "dealership": raw_ctx.dealership,
            "membership": raw_ctx.membership,
            "permissions": sorted(ctx.permissions),
            "features": ctx.features or {},
            "limits": ctx.limits or {},
        }

        serializer = MeSerializer(
            payload,
            context={"request": request},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)