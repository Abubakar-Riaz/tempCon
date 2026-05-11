# accounts/views/dealerships.py

from __future__ import annotations

from django.shortcuts import get_object_or_404

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Dealership
from accounts.serializers.dealerships import (
    DealershipCreateSerializer,
    DealershipListQuerySerializer,
    DealershipSerializer,
    DealershipUpdateSerializer,
)
from accounts.services.dealerships import (
    create_dealership,
    get_dealership_for_company_or_404,
    get_visible_dealerships,
    update_dealership,
)
from core.authz.request_context import _get_access_context


class DealershipListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw_ctx, ctx = _get_access_context(request)

        query = DealershipListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        page = query.validated_data["page"]
        page_size = query.validated_data["page_size"]

        qs = get_visible_dealerships(ctx)

        total = qs.count()
        start = (page - 1) * page_size
        items = qs[start:start + page_size]

        return Response(
            {
                "items": DealershipSerializer(items, many=True).data,
                "page": {
                    "number": page,
                    "size": page_size,
                    "total_items": total,
                    "total_pages": (total + page_size - 1) // page_size,
                },
            },
            status=status.HTTP_200_OK,
        )


class DealershipCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw_ctx, ctx = _get_access_context(request)

        serializer = DealershipCreateSerializer(
            data=request.data,
            context={"company": ctx.company},
        )
        serializer.is_valid(raise_exception=True)

        dealership = create_dealership(
            ctx=ctx,
            name=serializer.validated_data["name"],
        )

        return Response(
            DealershipSerializer(dealership).data,
            status=status.HTTP_201_CREATED,
        )


class DealershipDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, dealership_id):
        raw_ctx, ctx = _get_access_context(request)

        dealership = get_dealership_for_company_or_404(
            ctx=ctx,
            dealership_public_id=dealership_id,
        )

        return Response(
            DealershipSerializer(dealership).data,
            status=status.HTTP_200_OK,
        )


class DealershipUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, dealership_id):
        raw_ctx, ctx = _get_access_context(request)

        dealership = get_object_or_404(
            Dealership,
            public_id=dealership_id,
            company=ctx.company,
        )

        serializer = DealershipUpdateSerializer(
            dealership,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        dealership = update_dealership(
            ctx=ctx,
            dealership=dealership,
            data=serializer.validated_data,
        )

        return Response(
            DealershipSerializer(dealership).data,
            status=status.HTTP_200_OK,
        )