import secrets
import base64
from urllib.parse import urljoin
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from django.utils import timezone

from notifications.utils import send_email
from accounts.models import Invitation, Company, Dealership, InvitationKind


# ----------------------------
# URL helpers
# ----------------------------

def _base_url():
    return getattr(settings, "FRONTEND_URL", getattr(settings, "PUBLIC_BASE_URL", "https://app.buycon.com"))

def build_invite_activation_url(token: str) -> str:
    # Frontend deep link (recommended)
    fe_path = f"/invite/activate/?t={token}"
    return urljoin(_base_url(), fe_path)

# def build_api_activation_url(token: str) -> str:
#     api_path = reverse("staff-invite-activate", kwargs={"invitation_token": token})
#     return urljoin(_base_url(), api_path)


# ----------------------------
# Email HTML helpers (brand-aligned)
# ----------------------------

BRAND_NAME = "BuyCon"

# Brand tokens (HEX converted from your FE HSL for email safety)
_BRAND            = "#e64141"  # hsl(0,77%,58%)
_BRAND_DARK       = "#d91c1c"  # hsl(0,77%,48%)
_BRAND_LIGHT      = "#ec6f6f"  # hsl(0,77%,68%)
_BRAND_50         = "#fff0f1"  # hsl(355,100%,97%)
_BG               = "#ffffff"  # background
_BG_SECONDARY     = "#f3f4f6"  # background-secondary
_CARD             = "#ffffff"
_CARD_HOVER       = "#f9fafb"
_FOREGROUND       = "#14161a"  # foreground
_MUTED_FG         = "#667085"  # muted-foreground
_BORDER           = "#e5e7eb"
_FONT_STACK = '"Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif'


def _button_html(label: str, href: str) -> str:
    return (
        f"<table role='presentation' cellspacing='0' cellpadding='0' style='margin:18px 0'>"
        f"  <tr>"
        f"    <td align='center' style='border-radius:10px; background:{_BRAND};'>"
        f"      <a href='{href}' style='display:inline-block;padding:12px 18px;font-family:{_FONT_STACK};"
        f"         color:#ffffff;text-decoration:none;font-weight:700;font-size:15px;line-height:22px;'>"
        f"        {label}"
        f"      </a>"
        f"    </td>"
        f"  </tr>"
        f"</table>"
    )

def _invite_html(*, title: str, lead: str, details_html: str = "", cta_label: str | None = None, cta_href: str | None = None, footer_note: str | None = None) -> str:
    cta_block = _button_html(cta_label, cta_href) if (cta_label and cta_href) else ""
    foot = footer_note or "If you weren’t expecting this, you can ignore this email."
    return f"""\
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background:{_BG_SECONDARY};">
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background:{_BG_SECONDARY};">
    <tr>
      <td align="center" style="padding:24px;">
        <table role="presentation" width="100%" style="max-width:600px;background:{_CARD};border-radius:16px;overflow:hidden;border:1px solid {_BORDER};box-shadow:0 8px 18px rgba(16,24,40,0.06);">
          <tr>
            <td style="padding:20px 24px;background:{_BRAND};color:#ffffff;">
              <div style="font-family:{_FONT_STACK};font-size:18px;font-weight:700;line-height:24px;">{BRAND_NAME}</div>
              <div style="margin-top:2px;font-family:{_FONT_STACK};font-size:12px;opacity:0.9;">Invitation</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 24px 8px 24px;">
              <h1 style="margin:0 0 10px 0;font-family:{_FONT_STACK};font-size:22px;line-height:28px;color:{_FOREGROUND};font-weight:700;">{title}</h1>
              <p style="margin:0 0 14px 0;font-family:{_FONT_STACK};color:{_FOREGROUND};font-size:16px;line-height:26px;">{lead}</p>
              {details_html}
              {cta_block}
              <p style="margin:12px 0 0;font-family:{_FONT_STACK};color:{_MUTED_FG};font-size:13px;line-height:20px;">{foot}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:18px 24px;background:{_CARD_HOVER};color:{_MUTED_FG};border-top:1px solid {_BORDER};">
              <div style="font-family:{_FONT_STACK};font-size:12px;line-height:20px;">© {timezone.now().year} {BRAND_NAME}. All rights reserved.</div>
              <div style="margin-top:4px;font-family:{_FONT_STACK};font-size:12px;line-height:20px;">Transactional notice — manage your account in the app.</div>
            </td>
          </tr>
        </table>
        <div style="height:24px;"></div>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _details_table(rows: list[tuple[str, str]]) -> str:
    if not rows:
        return ""
    # Simple key/value block
    html_rows = []
    for k, v in rows:
        html_rows.append(
            f"<tr>"
            f"  <td style='padding:8px 0;font-family:{_FONT_STACK};font-size:14px;color:{_MUTED_FG};width:36%;vertical-align:top;'>{k}</td>"
            f"  <td style='padding:8px 0;font-family:{_FONT_STACK};font-size:14px;color:{_FOREGROUND};vertical-align:top;'>{v}</td>"
            f"</tr>"
        )
    return (
        f"<table role='presentation' width='100%' style='margin:8px 0 4px 0;border-collapse:collapse;'>"
        f"{''.join(html_rows)}"
        f"</table>"
    )


# ----------------------------
# Staff & vendor emails
# ----------------------------

def send_staff_invite_email(*, invitation: Invitation, company: Company, dealership: Dealership, roles: list[str]):
    token = invitation.token
    link = build_invite_activation_url(token)
    subject = f"You're invited to {company.name} — {dealership.name} on {BRAND_NAME}"

    # Details block
    details = _details_table([
        ("Company", company.name),
        ("Dealership", dealership.name),
        ("Role(s)", ", ".join(roles) if roles else "Member"),
    ])

    html = _invite_html(
        title="You’re invited",
        lead=f"You’ve been invited to join <strong>{company.name}</strong> — <strong>{dealership.name}</strong> on {BRAND_NAME}.",
        details_html=details,
        cta_label="Accept invitation",
        cta_href=link,
        footer_note="If you weren’t expecting this, you can ignore this email.",
    )
    body_text = (
        f"You’ve been invited to {company.name} — {dealership.name} on {BRAND_NAME}.\n"
        f"Roles: {', '.join(roles) if roles else 'Member'}\n\n"
        f"Accept invitation: {link}\n"
    )

    send_email(
        to=invitation.email,
        subject=subject,
        body=html,
        body_text=body_text,
        category="Staff",
        disable_tracking=False,
    )


def send_existing_user_added_email(*, email: str, company: Company, dealership: Dealership, roles: list[str]):
    subject = f"You've been added to {company.name} — {dealership.name} on {BRAND_NAME}"

    details = _details_table([
        ("Company", company.name),
        ("Dealership", dealership.name),
        ("Role(s)", ", ".join(roles) if roles else "Member"),
    ])

    html = _invite_html(
        title="Access granted",
        lead=f"You now have access to <strong>{company.name}</strong> — <strong>{dealership.name}</strong>.",
        details_html=details,
        cta_label="Open BuyCon",
        cta_href=_base_url(),
        footer_note=None,
    )
    body_text = (
        f"You now have access to {company.name} — {dealership.name} on {BRAND_NAME}.\n"
        f"Roles: {', '.join(roles) if roles else 'Member'}\n\n"
        f"Open: {_base_url()}\n"
    )

    send_email(
        to=email,
        subject=subject,
        body=html,
        body_text=body_text,
        category="Staff",
        disable_tracking=False,
    )


VENDOR_ROLE = "VENDOR"
VENDOR_TRADE_PREFIX = "VENDOR:"
VENDOR_NAME_PREFIX = "VENDOR_NAME:"  # ephemeral, used only to pass display name through activation


def _encode_name(name: str) -> str:
    return base64.urlsafe_b64encode((name or "").encode("utf-8")).decode("ascii")

def _decode_name(s: str) -> str:
    try:
        return base64.urlsafe_b64decode(s.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


def send_vendor_invite_email(*, invitation: Invitation, company: Company, dealership: Dealership, display_name: str):
    token = invitation.token
    link = build_invite_activation_url(token)
    subject = f"You're invited as a Vendor to {company.name} — {dealership.name} on {BRAND_NAME}"

    greet = f"Hi {display_name}," if (display_name or "").strip() else "Hi,"
    details = _details_table([
        ("Company", company.name),
        ("Dealership", dealership.name),
        ("Invitation", "Vendor account"),
    ])

    html = _invite_html(
        title="Vendor invitation",
        lead=f"{greet} You’ve been invited to <strong>{company.name}</strong> — <strong>{dealership.name}</strong> as a Vendor.",
        details_html=details,
        cta_label="Accept invitation",
        cta_href=link,
        footer_note="If you weren’t expecting this, you can ignore this email.",
    )
    body_text = (
        f"{greet}\nYou’ve been invited to {company.name} — {dealership.name} on {BRAND_NAME} as a Vendor.\n\n"
        f"Accept invitation: {link}\n"
    )

    # You can route vendor emails as "Staff" or a separate "Vendors" category; keeping "Staff" keeps analytics simple.
    send_email(
        to=invitation.email,
        subject=subject,
        body=html,
        body_text=body_text,
        category="Staff",
        disable_tracking=False,
    )


# ----------------------------
# Token generation & create flows
# ----------------------------

def generate_invitation_token(length_bytes: int = 32) -> str:
    """
    Generates a URL-safe unique token for Invitation.token (<=255 chars).
    Retries on the extremely unlikely chance of a collision.
    """
    while True:
        token = secrets.token_urlsafe(length_bytes)  # ~43 chars at 32 bytes
        if not Invitation.objects.filter(token=token).exists():
            return token


@transaction.atomic
def create_invitation(
    *,
    email: str,
    company: Company,
    dealership: Dealership | None,
    roles: list[str],
    invited_by,
    grant_company_admin: bool = False,
    send_email_now: bool = True
) -> Invitation:
    """
    Creates an Invitation with a securely generated unique token.
    Optionally sends the invite email immediately.
    """
    token = generate_invitation_token()
    inv = Invitation.objects.create(
        email=(email or "").strip().lower(),
        company=company,
        dealership=dealership,
        roles=roles or [],
        grant_company_admin=grant_company_admin,
        invited_by=invited_by,
        token=token,
    )
    if send_email_now and dealership:
        send_staff_invite_email(invitation=inv, company=company, dealership=dealership, roles=roles or [])
    return inv


@transaction.atomic
def create_vendor_invitation(
    *,
    email: str,
    name: str,
    company: Company,
    dealership: Dealership | None,
    trade_role_tokens: list[str],
    invited_by,
    send_email_now: bool = True,
) -> Invitation:
    """
    Create a VENDOR-kind invitation. We stash the display name and trade context as
    ephemeral role-like tokens for activation only, and will strip them after accept.
    """
    token = generate_invitation_token()
    # roles carry: "VENDOR" + trade-prefixed tokens + encoded name token
    roles = [VENDOR_ROLE, *trade_role_tokens, f"{VENDOR_NAME_PREFIX}{_encode_name(name or '')}"]
    inv = Invitation.objects.create(
        kind=InvitationKind.VENDOR,
        email=(email or "").strip().lower(),
        company=company,
        dealership=dealership,
        roles=roles,
        grant_company_admin=False,
        invited_by=invited_by,
        token=token,
    )
    if send_email_now and dealership:
        send_vendor_invite_email(invitation=inv, company=company, dealership=dealership, display_name=name or "")
    return inv


def parse_vendor_invite_context(inv: Invitation) -> tuple[str, list[str]]:
    """
    Returns (vendor_display_name, vendor_trade_tokens)
    """
    display_name = ""
    trade_tokens: list[str] = []
    for r in (inv.roles or []):
        if isinstance(r, str) and r.startswith(VENDOR_NAME_PREFIX):
            display_name = _decode_name(r[len(VENDOR_NAME_PREFIX):])
        elif isinstance(r, str) and r.startswith(VENDOR_TRADE_PREFIX):
            trade_tokens.append(r)
    return display_name, trade_tokens
