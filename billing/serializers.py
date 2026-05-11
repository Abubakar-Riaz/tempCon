from rest_framework import serializers

from billing.models import BillingInvoice, SubscriptionPlan, SubscriptionPlanPrice


class SubscriptionPlanPriceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = SubscriptionPlanPrice
        fields = [
            "id",
            "interval",
            "amount",
            "currency",
            "stripe_price_id",
        ]


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)
    prices = SubscriptionPlanPriceSerializer(many=True, read_only=True)

    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "feature_flags",
            "limits",
            "prices",
        ]


class BillingInvoiceSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="public_id", read_only=True)

    class Meta:
        model = BillingInvoice
        fields = [
            "id",
            "invoice_number",
            "status",
            "currency",
            "subtotal",
            "tax",
            "total",
            "amount_paid",
            "amount_remaining",
            "provider_hosted_invoice_url",
            "provider_invoice_pdf_url",
            "billing_reason",
            "collection_method",
            "period_start",
            "period_end",
            "due_at",
            "paid_at",
            "voided_at",
            "created_at",
        ]