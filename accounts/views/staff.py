# accounts/views/staff.py

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers.staff import (
    StaffMemberSerializer,
    StaffPermissionUpdateSerializer,
    StaffRoleUpdateSerializer,
)
from accounts.services.staff import (
    assert_can_view_staff,
    change_staff_role,
    get_staff_member_or_404,
    get_staff_queryset,
    remove_staff_member,
    update_staff_permissions,
)
from core.authz.request_context import _get_access_context


class StaffListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_ctx, ctx = _get_access_context(request)
        assert_can_view_staff(ctx)

        q = (request.query_params.get("q") or "").strip()
        role = (request.query_params.get("role") or "").strip().lower()

        limit = max(1, min(int(request.query_params.get("limit", 50)), 100))
        offset = max(0, int(request.query_params.get("offset", 0)))

        qs = get_staff_queryset(
            dealership=raw_ctx.dealership,
            search=q,
            role=role,
        )

        count = qs.count()
        items = qs[offset:offset + limit]

        return Response(
            {
                "count": count,
                "results": StaffMemberSerializer(items, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


class StaffRoleUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, member_id):
        raw_ctx, ctx = _get_access_context(request)

        serializer = StaffRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = get_object_or_404(
            get_staff_queryset(dealership=raw_ctx.dealership),
            public_id=member_id,
        )

        target = change_staff_role(
            ctx=ctx,
            target=target,
            roles=serializer.validated_data["roles"],
        )

        return Response(
            StaffMemberSerializer(target).data,
            status=status.HTTP_200_OK,
        )


class StaffPermissionUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, member_id):
        raw_ctx, ctx = _get_access_context(request)

        serializer = StaffPermissionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = get_object_or_404(
            get_staff_queryset(dealership=raw_ctx.dealership),
            public_id=member_id,
        )

        target = update_staff_permissions(
            ctx=ctx,
            target=target,
            allow=serializer.validated_data.get("allow", []),
            deny=serializer.validated_data.get("deny", []),
        )

        return Response(
            StaffMemberSerializer(target).data,
            status=status.HTTP_200_OK,
        )


class StaffRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, member_id):
        raw_ctx, ctx = _get_access_context(request)

        target = get_object_or_404(
            get_staff_queryset(dealership=raw_ctx.dealership),
            public_id=member_id,
        )

        remove_staff_member(ctx=ctx, target=target)

        return Response(status=status.HTTP_204_NO_CONTENT)