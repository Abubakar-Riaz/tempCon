# inspections/views/trades.py

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_permission

from inspections.models import Trade
from inspections.serializers import TradeSerializer


class TradesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ctx = _get_ctx(request)

        qs = Trade.objects.filter(
            company=ctx.company,
            is_active=True,
        ).order_by("order_index", "label")

        return Response(TradeSerializer(qs, many=True).data)


def _get_ctx(request):
    raw_ctx = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw_ctx.user,
        membership=raw_ctx.membership,
        dealership=raw_ctx.dealership,
        subscription=raw_ctx.subscription,
    )