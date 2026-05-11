from __future__ import annotations

from decimal import Decimal

from billing.models import (
    BillingInterval,
    BillingProvider,
    PlanCode,
    SubscriptionPlan,
    SubscriptionPlanPrice,
)
from core.authz.plans import PLAN_DEFAULT_FEATURES, PLAN_DEFAULT_LIMITS


STRIPE_PLAN_DATA: dict[str, dict] = {
    PlanCode.STARTER: {
        "product_id": "prod_REPLACE_STARTER",
        "prices": {
            BillingInterval.MONTHLY: "price_REPLACE_STARTER_MONTHLY",
            BillingInterval.YEARLY: "price_REPLACE_STARTER_YEARLY",
        },
    },
    PlanCode.GROWTH: {
        "product_id": "prod_REPLACE_GROWTH",
        "prices": {
            BillingInterval.MONTHLY: "price_REPLACE_GROWTH_MONTHLY",
            BillingInterval.YEARLY: "price_REPLACE_GROWTH_YEARLY",
        },
    },
    PlanCode.BUSINESS: {
        "product_id": "prod_REPLACE_BUSINESS",
        "prices": {
            BillingInterval.MONTHLY: "price_REPLACE_BUSINESS_MONTHLY",
            BillingInterval.YEARLY: "price_REPLACE_BUSINESS_YEARLY",
        },
    },
    PlanCode.ENTERPRISE: {
        "product_id": "prod_REPLACE_ENTERPRISE",
        "prices": {
            BillingInterval.MONTHLY: "price_REPLACE_ENTERPRISE_MONTHLY",
            BillingInterval.YEARLY: "price_REPLACE_ENTERPRISE_YEARLY",
        },
    },
}


PLAN_DEFINITIONS: dict[str, dict] = {
    PlanCode.STARTER: {
        "name": "Starter",
        "description": (
            "Perfect for smaller dealerships getting started.\n"
            "Single dealership\n"
            "Core inventory workflow\n"
            "VHR + inspections\n"
            "CSV imports\n"
            "Up to 3 users"
        ),
        "sort_order": 1,
        "prices": {
            BillingInterval.MONTHLY: Decimal("99.00"),
            BillingInterval.YEARLY: Decimal("999.00"),
        },
    },
    PlanCode.GROWTH: {
        "name": "Growth",
        "description": (
            "Built for growing dealership operations.\n"
            "Multi-dealership support\n"
            "Auction imports\n"
            "Vendor workflows\n"
            "Audit logs\n"
            "Up to 10 users"
        ),
        "sort_order": 2,
        "prices": {
            BillingInterval.MONTHLY: Decimal("299.00"),
            BillingInterval.YEARLY: Decimal("2999.00"),
        },
    },
    PlanCode.BUSINESS: {
        "name": "Business",
        "description": (
            "Advanced operational tooling for larger teams.\n"
            "Custom roles\n"
            "Advanced recon workflows\n"
            "Vendor management\n"
            "Expanded limits\n"
            "Up to 30 users"
        ),
        "sort_order": 3,
        "prices": {
            BillingInterval.MONTHLY: Decimal("799.00"),
            BillingInterval.YEARLY: Decimal("7999.00"),
        },
    },
    PlanCode.ENTERPRISE: {
        "name": "Enterprise",
        "description": (
            "Enterprise-grade scaling and support.\n"
            "Priority support\n"
            "High operational limits\n"
            "Large multi-store support\n"
            "Advanced workflows\n"
            "Up to 250 users"
        ),
        "sort_order": 4,
        "prices": {
            BillingInterval.MONTHLY: Decimal("1999.00"),
            BillingInterval.YEARLY: Decimal("19999.00"),
        },
    },
}


CURRENCY = "USD"
IS_ACTIVE = True
IS_PUBLIC = True


def validate_stripe_plan_data() -> None:
    missing: list[str] = []

    for plan_code, config in STRIPE_PLAN_DATA.items():
        if not config.get("product_id"):
            missing.append(f"{plan_code}: product_id")

        prices = config.get("prices", {})

        for interval in (
            BillingInterval.MONTHLY,
            BillingInterval.YEARLY,
        ):
            if not prices.get(interval):
                missing.append(f"{plan_code}: prices.{interval}")

    if missing:
        joined = "\n".join(f"- {item}" for item in missing)
        raise ValueError(f"Fill STRIPE_PLAN_DATA before running:\n{joined}")


def upsert_plan(plan_code: str) -> SubscriptionPlan:
    config = PLAN_DEFINITIONS[plan_code]
    stripe_config = STRIPE_PLAN_DATA[plan_code]

    plan, _ = SubscriptionPlan.objects.update_or_create(
        code=plan_code,
        defaults={
            "name": config["name"],
            "description": config["description"],
            "is_active": IS_ACTIVE,
            "is_public": IS_PUBLIC,
            "sort_order": config["sort_order"],
            "stripe_product_id": stripe_config["product_id"],
            "feature_flags": PLAN_DEFAULT_FEATURES[plan_code],
            "limits": PLAN_DEFAULT_LIMITS[plan_code],
        },
    )

    return plan


def upsert_plan_prices(plan: SubscriptionPlan) -> list[SubscriptionPlanPrice]:
    config = PLAN_DEFINITIONS[plan.code]
    stripe_config = STRIPE_PLAN_DATA[plan.code]

    saved_prices: list[SubscriptionPlanPrice] = []

    for interval, amount in config["prices"].items():
        price, _ = SubscriptionPlanPrice.objects.update_or_create(
            plan=plan,
            provider=BillingProvider.STRIPE,
            interval=interval,
            currency=CURRENCY,
            defaults={
                "amount": amount,
                "stripe_price_id": stripe_config["prices"][interval],
                "is_active": IS_ACTIVE,
                "is_public": IS_PUBLIC,
            },
        )

        saved_prices.append(price)

    return saved_prices


def seed_billing_plans(*, verbose: bool = True) -> None:
    validate_stripe_plan_data()

    for plan_code in (
        PlanCode.STARTER,
        PlanCode.GROWTH,
        PlanCode.BUSINESS,
        PlanCode.ENTERPRISE,
    ):
        plan = upsert_plan(plan_code)
        prices = upsert_plan_prices(plan)

        if verbose:
            print(
                f"[OK] plan={plan.code} "
                f"product={plan.stripe_product_id} "
                f"public_id={plan.public_id}"
            )

            for price in prices:
                print(
                    "   "
                    f"[OK] price interval={price.interval} "
                    f"amount={price.amount} {price.currency} "
                    f"stripe_price_id={price.stripe_price_id} "
                    f"public_id={price.public_id}"
                )


# Run:
# python manage.py shell
#
# >>> exec(open("billing/seeders/seed_billing_plans.py").read())
# >>> seed_billing_plans()