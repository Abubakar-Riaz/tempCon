from __future__ import annotations

import logging

from core.email import send_email

logger = logging.getLogger(__name__)


def _company_owner_email(company, fallback: str = "") -> str:
    owner = (
        company.memberships
        .select_related("user")
        .filter(is_company_owner=True, status="active")
        .first()
    )

    if owner and owner.user.email:
        return owner.user.email

    if getattr(company, "created_by", None) and company.created_by.email:
        return company.created_by.email

    return fallback or company.email or ""


def send_checkout_success_email(*, company, subscription, fallback_email: str = "") -> None:
    to_email = _company_owner_email(company, fallback_email)
    if not to_email or not subscription:
        return

    try:
        send_email(
            to_email=to_email,
            subject=f"Your {subscription.plan.name} plan is active",
            template_name="emails/billing/checkout_success.html",
            context={
                "company": company,
                "subscription": subscription,
                "plan": subscription.plan,
            },
        )
    except Exception:
        logger.exception("Failed sending checkout success email")


def send_invoice_payment_failed_email(*, company, invoice, fallback_email: str = "") -> None:
    to_email = _company_owner_email(company, fallback_email)
    if not to_email or not invoice:
        return

    try:
        send_email(
            to_email=to_email,
            subject="Payment failed for your BuyCon subscription",
            template_name="emails/billing/payment_failed.html",
            context={
                "company": company,
                "invoice": invoice,
            },
        )
    except Exception:
        logger.exception("Failed sending payment failed email")


def send_subscription_expired_email(*, company, subscription, fallback_email: str = "") -> None:
    to_email = _company_owner_email(company, fallback_email)
    if not to_email or not subscription:
        return

    try:
        send_email(
            to_email=to_email,
            subject="Your BuyCon subscription has expired",
            template_name="emails/billing/subscription_expired.html",
            context={
                "company": company,
                "subscription": subscription,
                "plan": subscription.plan,
            },
        )
    except Exception:
        logger.exception("Failed sending subscription expired email")