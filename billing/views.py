from __future__ import annotations

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.serializers import BillingInvoiceSerializer, SubscriptionPlanSerializer
from billing.services import (
    BillingError,
    create_checkout_session,
    create_portal_session,
    get_billing_overview,
    get_company_invoices,
    get_featured_plan,
    get_public_plans,
)
from core.authz.features import Features
from core.authz.permissions import Permissions
from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context, has_feature, has_permission


def _frontend_url(path: str) -> str:
    base = getattr(settings, "FRONTEND_BASE_URL", "https://dev.salescribe.ai").rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _get_billing_ctx(request):
    raw = resolve_request_dealership_context(request)
    ctx = build_access_context(
        user=raw.user,
        membership=raw.membership,
        dealership=raw.dealership,
        subscription=raw.subscription,
    )

    if not has_feature(ctx, Features.BILLING):
        raise PermissionDenied("Billing is not available on your plan.")

    return raw, ctx


class BillingPlansView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        serializer = SubscriptionPlanSerializer(get_public_plans(), many=True)
        return Response({"plans": serializer.data}, status=status.HTTP_200_OK)


class BillingOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw, ctx = _get_billing_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_BILLING):
            raise PermissionDenied("You do not have permission to view billing.")

        overview = get_billing_overview(raw.company)
        subscription = overview.subscription

        data = {
            "company": {
                "id": raw.company.public_id,
                "name": raw.company.name,
            },
            "subscription": None,
            "payment_method": overview.payment_method,
            "usage": overview.usage,
            "features": overview.features,
            "limits": overview.limits,
            "portal_available": bool(
                overview.customer and overview.customer.provider_customer_id
            ),
        }

        if subscription:
            data["subscription"] = {
                "id": subscription.public_id,
                "status": subscription.status,
                "plan": {
                    "id": subscription.plan.public_id,
                    "code": subscription.plan.code,
                    "name": subscription.plan.name,
                    "description": subscription.plan.description,
                },
                "plan_price": {
                    "id": subscription.plan_price.public_id,
                    "interval": subscription.plan_price.interval,
                    "amount": str(subscription.plan_price.amount),
                    "currency": subscription.plan_price.currency,
                } if subscription.plan_price else None,
                "starts_at": subscription.starts_at,
                "ends_at": subscription.ends_at,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "cancel_at": subscription.cancel_at,
                "canceled_at": subscription.canceled_at,
                "ended_at": subscription.ended_at,
            }

        return Response(data, status=status.HTTP_200_OK)


class BillingCheckoutSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw, ctx = _get_billing_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_BILLING):
            raise PermissionDenied("You do not have permission to manage billing.")

        plan_code = (request.data.get("plan_code") or "").strip()
        interval = (request.data.get("interval") or "").strip()

        if not plan_code:
            return Response({"detail": "plan_code is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not interval:
            return Response({"detail": "interval is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            checkout_url = create_checkout_session(
                company=raw.company,
                user=request.user,
                plan_code=plan_code,
                interval=interval,
                success_url=_frontend_url("checkout/success"),
                cancel_url=_frontend_url("checkout/cancel"),
            )
        except BillingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"checkout_url": checkout_url}, status=status.HTTP_200_OK)


class BillingPortalSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        raw, ctx = _get_billing_ctx(request)

        if not has_permission(ctx, Permissions.MANAGE_BILLING):
            raise PermissionDenied("You do not have permission to manage billing.")

        try:
            portal_url = create_portal_session(
                company=raw.company,
                return_url=_frontend_url("pricing"),
            )
        except BillingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"portal_url": portal_url}, status=status.HTTP_200_OK)


class BillingInvoiceListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        raw, ctx = _get_billing_ctx(request)

        if not has_permission(ctx, Permissions.VIEW_BILLING):
            raise PermissionDenied("You do not have permission to view billing.")

        serializer = BillingInvoiceSerializer(
            get_company_invoices(raw.company),
            many=True,
        )

        return Response({"invoices": serializer.data}, status=status.HTTP_200_OK)


class PromotionFeaturedCardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plan = get_featured_plan()

        if not plan:
            return Response({"featured_card": None}, status=status.HTTP_200_OK)

        serializer = SubscriptionPlanSerializer(plan)

        return Response(
            {
                "featured_card": {
                    "title": "Upgrade your dealership workflow",
                    "subtitle": "Unlock higher limits and more tools for your team.",
                    "plan": serializer.data,
                }
            },
            status=status.HTTP_200_OK,
        )