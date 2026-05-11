from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Company
from core.models.base import PublicIDModel, TimestampedModel


class BillingInterval(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class BillingProvider(models.TextChoices):
    STRIPE = "stripe", "Stripe"


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past Due"
    CANCELED = "canceled", "Canceled"
    EXPIRED = "expired", "Expired"
    INCOMPLETE = "incomplete", "Incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired", "Incomplete Expired"
    UNPAID = "unpaid", "Unpaid"


class PlanCode(models.TextChoices):
    STARTER = "starter", "Starter"
    GROWTH = "growth", "Growth"
    BUSINESS = "business", "Business"
    ENTERPRISE = "enterprise", "Enterprise"


class SubscriptionPlan(PublicIDModel, TimestampedModel):
    code = models.CharField(
        max_length=50,
        choices=PlanCode.choices,
        unique=True,
        db_index=True,
    )

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")

    is_active = models.BooleanField(default=True, db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    stripe_product_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    feature_flags = models.JSONField(default=dict, blank=True)
    limits = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_subscription_plan"
        ordering = ["sort_order", "created_at"]
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["code"]),
            models.Index(fields=["is_active", "is_public"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def get_feature_flag(self, key: str, default=None):
        return (self.feature_flags or {}).get(key, default)

    def get_limit(self, key: str, default=None):
        return (self.limits or {}).get(key, default)


class SubscriptionPlanPrice(PublicIDModel, TimestampedModel):
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="prices",
    )

    provider = models.CharField(
        max_length=50,
        choices=BillingProvider.choices,
        default=BillingProvider.STRIPE,
        db_index=True,
    )

    interval = models.CharField(
        max_length=20,
        choices=BillingInterval.choices,
        db_index=True,
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")

    stripe_price_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )

    is_active = models.BooleanField(default=True, db_index=True)
    is_public = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "billing_subscription_plan_price"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["plan", "is_active", "is_public"]),
            models.Index(fields=["provider", "interval"]),
            models.Index(fields=["currency"]),
            models.Index(fields=["stripe_price_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "provider", "interval", "currency"],
                name="uniq_plan_provider_interval_currency_price",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan.name} / {self.interval} / {self.amount} {self.currency}"


class CompanySubscription(PublicIDModel, TimestampedModel):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )

    plan_price = models.ForeignKey(
        SubscriptionPlanPrice,
        on_delete=models.PROTECT,
        related_name="subscriptions",
        null=True,
        blank=True,
    )

    provider = models.CharField(
        max_length=50,
        choices=BillingProvider.choices,
        default=BillingProvider.STRIPE,
        db_index=True,
    )

    provider_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )
    provider_product_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )
    provider_price_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )

    status = models.CharField(
        max_length=32,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INCOMPLETE,
        db_index=True,
    )

    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)

    cancel_at_period_end = models.BooleanField(default=False, db_index=True)
    cancel_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    feature_flags_override = models.JSONField(default=dict, blank=True)
    limits_override = models.JSONField(default=dict, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default="")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_company_subscriptions",
    )

    class Meta:
        db_table = "billing_company_subscription"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["status"]),
            models.Index(fields=["provider", "provider_subscription_id"]),
            models.Index(fields=["starts_at"]),
            models.Index(fields=["ends_at"]),
            models.Index(fields=["current_period_end"]),
            models.Index(fields=["cancel_at_period_end"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_subscription_id"],
                condition=~models.Q(provider_subscription_id=""),
                name="uniq_provider_subscription_id_nonempty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company.name} -> {self.plan.name} [{self.status}]"

    @property
    def is_active_effective(self) -> bool:
        if self.status not in {
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.PAST_DUE,
        }:
            return False

        now = timezone.now()

        if self.ended_at and self.ended_at <= now:
            return False

        if self.ends_at and self.ends_at <= now:
            return False

        return True

    def get_feature_flag(self, key: str, default=None):
        if key in (self.feature_flags_override or {}):
            return self.feature_flags_override[key]
        return self.plan.get_feature_flag(key, default)

    def get_limit(self, key: str, default=None):
        if key in (self.limits_override or {}):
            return self.limits_override[key]
        return self.plan.get_limit(key, default)

    def get_effective_features(self) -> dict:
        data = dict(self.plan.feature_flags or {})
        data.update(self.feature_flags_override or {})
        return data

    def get_effective_limits(self) -> dict:
        data = dict(self.plan.limits or {})
        data.update(self.limits_override or {})
        return data


class BillingCustomer(PublicIDModel, TimestampedModel):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="billing_customer",
    )

    provider = models.CharField(
        max_length=50,
        choices=BillingProvider.choices,
        default=BillingProvider.STRIPE,
        db_index=True,
    )

    provider_customer_id = models.CharField(max_length=255, db_index=True)

    email = models.EmailField(blank=True, default="")
    name = models.CharField(max_length=255, blank=True, default="")

    default_payment_method_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
    )
    default_payment_method_type = models.CharField(max_length=50, blank=True, default="")
    default_payment_method_brand = models.CharField(max_length=50, blank=True, default="")
    default_payment_method_last4 = models.CharField(max_length=10, blank=True, default="")
    default_payment_method_exp_month = models.PositiveSmallIntegerField(null=True, blank=True)
    default_payment_method_exp_year = models.PositiveSmallIntegerField(null=True, blank=True)
    default_payment_method_updated_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "billing_customer"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["provider", "provider_customer_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_customer_id"],
                name="uniq_billing_customer_provider_customer_id",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.provider_customer_id}"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    OPEN = "open", "Open"
    PAID = "paid", "Paid"
    UNCOLLECTIBLE = "uncollectible", "Uncollectible"
    VOID = "void", "Void"


class BillingInvoice(PublicIDModel, TimestampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="billing_invoices",
    )

    customer = models.ForeignKey(
        BillingCustomer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    subscription = models.ForeignKey(
        CompanySubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    provider = models.CharField(
        max_length=50,
        choices=BillingProvider.choices,
        default=BillingProvider.STRIPE,
        db_index=True,
    )

    provider_invoice_id = models.CharField(max_length=255, db_index=True, blank=True, default="")
    provider_customer_id = models.CharField(max_length=255, db_index=True, blank=True, default="")
    provider_subscription_id = models.CharField(max_length=255, db_index=True, blank=True, default="")
    provider_payment_intent_id = models.CharField(max_length=255, db_index=True, blank=True, default="")

    provider_hosted_invoice_url = models.URLField(blank=True, default="")
    provider_invoice_pdf_url = models.URLField(blank=True, default="")

    invoice_number = models.CharField(max_length=100, blank=True, default="", db_index=True)

    currency = models.CharField(max_length=10, default="USD")

    status = models.CharField(
        max_length=32,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        db_index=True,
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_remaining = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    billing_reason = models.CharField(max_length=100, blank=True, default="")
    collection_method = models.CharField(max_length=50, blank=True, default="")

    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)

    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)
    raw_line_items = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "billing_invoice"
        indexes = [
            models.Index(fields=["public_id"]),
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["provider", "provider_invoice_id"]),
            models.Index(fields=["provider_customer_id"]),
            models.Index(fields=["provider_subscription_id"]),
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["due_at"]),
            models.Index(fields=["paid_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_invoice_id"],
                condition=~models.Q(provider_invoice_id=""),
                name="uniq_billing_invoice_provider_invoice_id_nonempty",
            ),
        ]

    def __str__(self) -> str:
        ident = self.invoice_number or self.provider_invoice_id or self.public_id
        return f"{self.company.name} / {ident} / {self.status}"