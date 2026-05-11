# core/email.py

from __future__ import annotations

from django.conf import settings
from django.template.loader import render_to_string
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_email(
    *,
    to_email: str,
    subject: str,
    template_name: str,
    context: dict | None = None,
    from_email: str | "None" = None,
    from_name: str = "BuyCon",
):
    if not settings.SENDGRID_API_KEY:
        raise RuntimeError("SENDGRID_API_KEY not configured")

    sender_email = from_email or settings.DEFAULT_FROM_EMAIL or "hello@buycon.com"
    html = render_to_string(
        template_name,
        {
            "brand_name": from_name,
            **(context or {}),
        },
    )

    message = Mail(
        from_email=(sender_email, from_name),
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
    except Exception as exc:
        raise RuntimeError(f"SendGrid email failed: {str(exc)}") from exc