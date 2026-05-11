# inventory/views/folders.py

from __future__ import annotations

from django.db import transaction
from django.utils.dateparse import parse_date

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inventory.models import Folder, FolderType
from inventory.serializers.folders import FolderCreateSerializer


class FolderPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _folder_payload(folder: Folder) -> dict:
    return {
        "id": folder.public_id,
        "name": folder.name,
        "type": folder.type,
        "date_bucket": folder.date_bucket,
        "created_by": (
            {
                "id": folder.created_by.public_id,
                "email": folder.created_by.email,
                "name": folder.created_by.display_name,
            }
            if folder.created_by
            else None
        ),
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )


def _parse_bool(value, *, default: bool = False) -> bool:
    if value is None:
        return default

    return str(value).strip().lower() in {"1", "true", "yes", "y"}


class FolderListView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = FolderPagination

    def get(self, request):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_INVENTORY):
            return Response(
                {"detail": "You do not have permission to view inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qs = (
            Folder.objects
            .select_related("created_by")
            .filter(
                company=ctx.company,
                dealership=ctx.dealership,
            )
        )

        if not has_permission(ctx, Permissions.MANAGE_INVENTORY):
            qs = qs.filter(created_by=request.user)

        include_auto = _parse_bool(
            request.query_params.get("include_auto"),
            default=False,
        )

        if not include_auto:
            qs = qs.filter(type=FolderType.MANUAL)

        folder_type = (request.query_params.get("type") or "").strip()

        if folder_type:
            valid_types = {choice for choice, _ in FolderType.choices}

            if folder_type not in valid_types:
                return Response(
                    {
                        "detail": "Invalid folder type.",
                        "valid_types": sorted(valid_types),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            qs = qs.filter(type=folder_type)

        date_bucket = (request.query_params.get("date_bucket") or "").strip()

        if date_bucket:
            parsed_date = parse_date(date_bucket)

            if not parsed_date:
                return Response(
                    {"detail": "date_bucket must be YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            qs = qs.filter(date_bucket=parsed_date)

        search = (request.query_params.get("q") or "").strip()

        if search:
            qs = qs.filter(name__icontains=search)

        ordering = (request.query_params.get("ordering") or "-created_at").strip()
        allowed_ordering = {
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "name",
            "-name",
            "type",
            "-type",
            "date_bucket",
            "-date_bucket",
        }

        if ordering not in allowed_ordering:
            return Response(
                {
                    "detail": "Invalid ordering.",
                    "valid_ordering": sorted(allowed_ordering),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = qs.order_by(ordering)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request)

        return paginator.get_paginated_response(
            [_folder_payload(folder) for folder in page]
        )


class FolderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        ctx = _get_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_INVENTORY):
            return Response(
                {"detail": "You do not have permission to manage inventory."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = FolderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        base_name = serializer.validated_data["name"]

        existing_qs = Folder.objects.filter(
            company=ctx.company,
            dealership=ctx.dealership,
            type=FolderType.MANUAL,
            name__istartswith=base_name,
        )

        if existing_qs.filter(name__iexact=base_name).exists():
            final_name = f"{base_name} ({existing_qs.count() + 1})"
        else:
            final_name = base_name

        folder = Folder.objects.create(
            company=ctx.company,
            dealership=ctx.dealership,
            name=final_name,
            type=FolderType.MANUAL,
            created_by=request.user,
            date_bucket=None,
        )

        return Response(
            _folder_payload(folder),
            status=status.HTTP_201_CREATED,
        )