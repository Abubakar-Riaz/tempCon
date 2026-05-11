from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from billing.models import InvoiceStatus, SubscriptionStatus


def obj_get(data: Any, key: str, default=None):
    if data is None:
        return default

    if isinstance(data, dict):
        return data.get(key, default)

    return getattr(data, key, default)


def dt_from_unix(value: int | None):
    if not value:
        return None

    return datetime.fromtimestamp(value, tz=UTC)


def amount_from_cents(value: int | None) -> Decimal:
    return Decimal(value or 0) / Decimal("100")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [json_safe(item) for item in value]

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def get_metadata(obj: Any) -> dict:
    metadata = obj_get(obj, "metadata", {}) or {}
    return metadata if isinstance(metadata, dict) else {}


def get_customer_id(obj: Any) -> str:
    customer = obj_get(obj, "customer", "") or ""

    if isinstance(customer, dict):
        return customer.get("id", "") or ""

    return str(customer or "")


def get_subscription_id(obj: Any) -> str:
    subscription = obj_get(obj, "subscription", "") or ""

    if isinstance(subscription, dict):
        return subscription.get("id", "") or ""

    return str(subscription or "")


def get_price_id_from_subscription(subscription_obj: Any) -> str:
    items = obj_get(subscription_obj, "items")
    items_data = obj_get(items, "data", []) or []

    if not items_data:
        return ""

    price = obj_get(items_data[0], "price")
    return str(obj_get(price, "id", "") or "")


def get_product_id_from_subscription(subscription_obj: Any) -> str:
    items = obj_get(subscription_obj, "items")
    items_data = obj_get(items, "data", []) or []

    if not items_data:
        return ""

    price = obj_get(items_data[0], "price")
    product = obj_get(price, "product", "") if price else ""

    if isinstance(product, dict):
        return str(product.get("id", "") or "")

    return str(product or "")


def map_subscription_status(value: str | None) -> str:
    mapping = {
        "trialing": SubscriptionStatus.ACTIVE,
        "active": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "unpaid": SubscriptionStatus.UNPAID,
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "incomplete_expired": SubscriptionStatus.INCOMPLETE_EXPIRED,
    }

    return mapping.get(value or "", SubscriptionStatus.ACTIVE)


def map_invoice_status(value: str | None) -> str:
    mapping = {
        "draft": InvoiceStatus.DRAFT,
        "open": InvoiceStatus.OPEN,
        "paid": InvoiceStatus.PAID,
        "uncollectible": InvoiceStatus.UNCOLLECTIBLE,
        "void": InvoiceStatus.VOID,
    }

    return mapping.get(value or "", InvoiceStatus.DRAFT)


def extract_invoice_line_items(invoice_obj: Any) -> list[dict]:
    lines = obj_get(invoice_obj, "lines")
    data = obj_get(lines, "data", []) or []

    items: list[dict] = []

    for line in data:
        price = obj_get(line, "price")
        period = obj_get(line, "period", {}) or {}

        items.append(
            {
                "id": obj_get(line, "id", "") or "",
                "description": obj_get(line, "description", "") or "",
                "amount": str(amount_from_cents(obj_get(line, "amount", 0))),
                "currency": (obj_get(line, "currency", "") or "").upper(),
                "quantity": obj_get(line, "quantity"),
                "price_id": obj_get(price, "id", "") if price else "",
                "product_id": obj_get(price, "product", "") if price else "",
                "period_start": dt_from_unix(obj_get(period, "start")),
                "period_end": dt_from_unix(obj_get(period, "end")),
            }
        )

    return items


def extract_stripe_identifiers(payload: dict) -> dict:
    event_type = payload.get("type", "") or ""
    data_object = ((payload.get("data") or {}).get("object") or {})

    customer_id = ""
    subscription_id = ""
    invoice_id = ""
    checkout_session_id = ""
    payment_intent_id = ""

    if event_type.startswith("customer.subscription."):
        customer_id = obj_get(data_object, "customer", "") or ""
        subscription_id = obj_get(data_object, "id", "") or ""

    elif event_type.startswith("invoice."):
        customer_id = obj_get(data_object, "customer", "") or ""
        subscription_id = obj_get(data_object, "subscription", "") or ""
        invoice_id = obj_get(data_object, "id", "") or ""
        payment_intent_id = obj_get(data_object, "payment_intent", "") or ""

    elif event_type.startswith("checkout.session."):
        customer_id = obj_get(data_object, "customer", "") or ""
        subscription_id = obj_get(data_object, "subscription", "") or ""
        invoice_id = obj_get(data_object, "invoice", "") or ""
        checkout_session_id = obj_get(data_object, "id", "") or ""
        payment_intent_id = obj_get(data_object, "payment_intent", "") or ""

    elif event_type.startswith("customer."):
        customer_id = obj_get(data_object, "id", "") or ""

    elif event_type.startswith("payment_method."):
        customer_id = obj_get(data_object, "customer", "") or ""

    return {
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "invoice_id": invoice_id,
        "checkout_session_id": checkout_session_id,
        "payment_intent_id": payment_intent_id,
    }