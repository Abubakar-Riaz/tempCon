import logging
from typing import Optional

from django.conf import settings
from django.utils.html import strip_tags

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Email, To, Content, Category, ReplyTo,
    TrackingSettings, ClickTracking, OpenTracking,
    MailSettings
)
from python_http_client.exceptions import HTTPError

logger = logging.getLogger(__name__)


def send_email(
    *,
    to: str,
    subject: str,
    body: str,  # HTML
    body_text: Optional[str] = None,
    category: Optional[str] = None,
    disable_tracking: bool = False,
) -> None:
    """
    Sends an email via SendGrid.

    Args:
        to: Recipient email.
        subject: Message subject.
        body: HTML body (required).
        body_text: Optional plain-text fallback (recommended).
        category: Optional SendGrid category (e.g., "OTP", "Payments").
        disable_tracking: If True, disables open/click tracking (use for OTP/security).
    """
    if not getattr(settings, "SENDGRID_API_KEY", None):
        logger.error("SENDGRID_API_KEY is not set; email not sent.")
        return

    from_email = Email(
        getattr(settings, "EMAIL_FROM_ADDRESS", "no-reply@example.com"),
        getattr(settings, "EMAIL_FROM_NAME", None) or None,
    )

    msg = Mail(
        from_email=from_email,
        to_emails=To(to),
        subject=subject,
    )

    # Plain text (fallback) and HTML parts
    plain = body_text if body_text is not None else strip_tags(body)
    msg.add_content(Content("text/plain", plain or ""))
    msg.add_content(Content("text/html", body))

    # Optional Reply-To from settings
    reply_to_addr = getattr(settings, "EMAIL_REPLY_TO", None)
    if reply_to_addr:
        msg.reply_to = ReplyTo(reply_to_addr)

    # Optional category
    if category:
        msg.add_category(Category(category))

    # Tracking settings
    tracking = TrackingSettings()
    tracking.click_tracking = ClickTracking(enable=not disable_tracking, enable_text=not disable_tracking)
    tracking.open_tracking = OpenTracking(enable=not disable_tracking)
    msg.tracking_settings = tracking

    # Sandbox mode (useful for staging/dev)
    mail_settings = MailSettings()
    msg.mail_settings = mail_settings

    # Send with retries on transient errors
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            response = sg.send(msg)
            status = getattr(response, "status_code", None)
            if 200 <= (status or 0) < 300:
                message_id = response.headers.get("X-Message-Id") or response.headers.get("X-Message-Id".lower())
                logger.info(
                    "EMAIL sent (to=%s, subject=%r, category=%s, sandbox=%s, status=%s, msg_id=%s)",
                    to, subject, category or "-", status, message_id or "-"
                )
                return
            else:
                logger.warning(
                    "EMAIL non-2xx (attempt %d/%d) to=%s status=%s body=%s",
                    attempt, max_attempts, to, status, getattr(response, "body", b"")[:500]
                )
        except HTTPError as e:
            # Retry on 429/5xx; log others and stop
            status = getattr(e, "status_code", None)
            body_preview = getattr(e, "body", b"")[:500]
            if status in (429, 500, 502, 503, 504) and attempt < max_attempts:
                logger.warning(
                    "EMAIL transient error (attempt %d/%d) to=%s status=%s body=%s",
                    attempt, max_attempts, to, status, body_preview
                )
            else:
                logger.error(
                    "EMAIL send failed (attempt %d/%d) to=%s status=%s body=%s",
                    attempt, max_attempts, to, status, body_preview
                )
                return
        except Exception as e:
            # Unknown failure — log and stop (don’t raise)
            logger.exception("EMAIL unexpected failure (attempt %d/%d) to=%s: %s", attempt, max_attempts, to, e)
            return
