from __future__ import annotations

import json
import typing as t
from dataclasses import dataclass, field
from datetime import datetime

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


from accounts.models import Company, Dealership  # scope
from audit.models import AuditLog, AuditAction   # your models
from backend.constants import * 




# =========================
# REQUEST-LOCAL STATE
# =========================

@dataclass
class AuditEntry:
    action: str                                  # AuditAction value
    target: t.Any                                # model instance (required)
    before: t.Optional[t.Mapping] = None         # keep small, redacted
    after: t.Optional[t.Mapping] = None          # keep small, redacted
    actor: t.Optional[t.Any] = None              # overrides request.user if given
    company: t.Optional[Company] = None          # overrides ctx company
    dealership: t.Optional[Dealership] = None    # overrides ctx dealership


@dataclass
class AuditContext:
    company: t.Optional[Company] = None
    dealership: t.Optional[Dealership] = None
    security_event: t.Optional[dict] = None      # e.g., {"code": "PLAN_LIMIT_REACHED", "action": "dealership.create"}
    started_at: datetime = field(default_factory=timezone.now)

# =========================
# SMALL HELPERS
# =========================

def _redact(value: t.Any) -> t.Any:
    """RECURSIVE REDACTION FOR SENSITIVE KEYS (MOVE SENSITIVE_KEYS TO constants.py)."""
    try:
        if isinstance(value, dict):
            return {k: ("***" if k.lower() in SENSITIVE_KEYS else _redact(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [_redact(v) for v in value]
        if isinstance(value, tuple):
            return tuple(_redact(v) for v in value)
        # make non-serializable types safe
        if isinstance(value, (datetime,)):
            return value.isoformat()
        return value
    except Exception:
        return str(value)

def _prepare_snapshot(obj: t.Optional[t.Mapping]) -> t.Optional[dict]:
    """ENSURE SNAPSHOTS ARE SMALL; TRUNCATE IF NEEDED (MOVE LIMITS TO constants.py)."""
    if obj is None:
        return None
    safe_obj = _redact(obj)
    try:
        s = json.dumps(safe_obj, default=str)
    except Exception:
        s = json.dumps(str(safe_obj))
    if len(s) <= MAX_SNAPSHOT_CHARS:
        # return original dict (better for querying)
        return safe_obj if isinstance(safe_obj, dict) else {"value": safe_obj}
    # truncated preview payload
    return {"_truncated": True, "_preview": s[:MAX_SNAPSHOT_CHARS], "_size": len(s)}

def _get_ip(request: HttpRequest) -> t.Optional[str]:
    """BASIC IP EXTRACTION; ADAPT IF BEHIND PROXIES (MOVE HEADER NAME TO constants.py)."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")

def _get_user_agent(request: HttpRequest) -> t.Optional[str]:
    ua = request.META.get("HTTP_USER_AGENT")
    if not ua:
        return None
    # trim very long UAs
    return ua[:255]

def _content_type_and_id(obj: t.Any) -> t.Tuple[t.Optional[ContentType], t.Optional[int]]:
    if obj is None:
        return None, None
    try:
        ct = ContentType.objects.get_for_model(obj, for_concrete_model=False)
        oid = getattr(obj, "pk", None) or getattr(obj, "id", None)
        return ct, int(oid) if oid is not None else None
    except Exception:
        return None, None

def _maybe_excerpt_request(request: HttpRequest) -> t.Optional[dict]:
    """OPTIONAL EXCERPTS (DISABLED BY DEFAULT; TURN ON PER YOUR PRIVACY RULES)."""
    if not CAPTURE_REQUEST_EXCERPTS:
        return None
    out = {}
    try:
        if request.GET:
            out["query"] = {k: request.GET.get(k) for k in list(request.GET.keys())[:30]}
        if request.body:
            body = request.body.decode(errors="ignore")
            out["body"] = body[:EXCERPT_MAX_CHARS]
    except Exception:
        pass
    return out or None

def _maybe_excerpt_response(response: HttpResponse) -> t.Optional[dict]:
    if not CAPTURE_RESPONSE_EXCERPTS:
        return None
    out = {}
    try:
        if getattr(response, "content", None):
            out["body"] = response.content[:EXCERPT_MAX_CHARS].decode(errors="ignore")
    except Exception:
        pass
    return out or None

# =========================
# PUBLIC HELPER FOR VIEWS
# =========================

def audit_event(
    request: HttpRequest,
    *,
    action: str,
    target: t.Any,
    before: t.Optional[t.Mapping] = None,
    after: t.Optional[t.Mapping] = None,
    actor: t.Optional[t.Any] = None,
    company: t.Optional[Company] = None,
    dealership: t.Optional[Dealership] = None,
) -> None:
    """
    QUEUE AN AUDIT ENTRY FROM A VIEW/SERVICE.
    - USE SMALL, REDACTED SNAPSHOTS FOR before/after (SEE SENSITIVE_KEYS ABOVE).
    """
    ctx: AuditContext = getattr(request, "_audit_ctx", AuditContext())
    entries: list[AuditEntry] = getattr(request, "_audit_entries", [])
    entries.append(
        AuditEntry(
            action=action,
            target=target,
            before=before,
            after=after,
            actor=actor,
            company=company,
            dealership=dealership,
        )
    )
    request._audit_entries = entries
    request._audit_ctx = ctx  # ensure ctx exists

# =========================
# THE MIDDLEWARE
# =========================

class AuditMiddleware:
    """
    AUDIT MIDDLEWARE
    - Creates a request-scoped AuditContext
    - Lets views/decorators queue entries (via `audit_event`), and flushes them post-response
    - Also records security/denial events set by permission decorator in `request._audit_ctx["security_event"]`
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:

        if not hasattr(request, "_audit_ctx"):
            request._audit_ctx = AuditContext()
        if not hasattr(request, "_audit_entries"):
            request._audit_entries = []  # type: ignore # type: list[AuditEntry]

        # OPTIONAL: expose a convenience method on the request
        request.audit = lambda **kw: audit_event(request, **kw)  # type: ignore[attr-defined]

        # PROCESS REQUEST
        try:
            response = self.get_response(request)
        except Exception:
            # OPTIONAL: record a server error audit (without leaking sensitive data)
            self._write_security_event(request, status_code=500, deny_code="SERVER_ERROR", attempted_action=None)
            raise

        # AFTER RESPONSE: FLUSH ENTRIES
        self._flush(request, response)
        return response

    # -------------------------
    # INTERNALS
    # -------------------------

    def _flush(self, request: HttpRequest, response: HttpResponse) -> None:
        ctx: AuditContext = getattr(request, "_audit_ctx", AuditContext())
        entries: list[AuditEntry] = getattr(request, "_audit_entries", [])

        # SECURITY EVENT FOR DENIALS (SET BY PERMISSION DECORATOR)
        if getattr(ctx, "security_event", None) and response.status_code >= 400:
            self._write_security_event(
                request,
                status_code=response.status_code,
                deny_code=str(ctx.security_event.get("code")),
                attempted_action=str(ctx.security_event.get("action")),
            )

        # BASELINE ENTRY (OPTIONAL)
        if ALWAYS_WRITE_BASELINE_ENTRY and not entries and response.status_code < 400:
            # synthesize a minimal “request completed” entry targeted at company
            if ctx.company:
                audit = AuditEntry(
                    action=AuditAction.OTHER,
                    target=ctx.company,
                    before=None,
                    after={"ok": True, "status": response.status_code},
                    actor=getattr(request, "user", None) if getattr(request, "user", None) and request.user.is_authenticated else None,
                )
                entries = [audit]

        if not entries:
            return

        ip = _get_ip(request)
        ua = _get_user_agent(request)

        def _write_one(entry: AuditEntry):
            # Resolve actor
            actor = entry.actor or (request.user if getattr(request, "user", None) and request.user.is_authenticated else None)
            actor_ct, actor_id = _content_type_and_id(actor)

            # Resolve target
            target_ct, target_id = _content_type_and_id(entry.target)
            if not target_ct or not target_id:
                return  # cannot write without a concrete target

            # Resolve scope (company/dealership)
            company = entry.company or ctx.company or getattr(entry.target, "company", None)
            if not isinstance(company, Company):
                # COMPANY IS REQUIRED BY MODEL; SKIP IF UNKNOWN
                return  # >>> IF YOU WANT PLATFORM-WIDE ROWS, DEFINE A SYSTEM COMPANY AND USE IT HERE

            dealership = entry.dealership or ctx.dealership or getattr(entry.target, "dealership", None)
            if dealership and not isinstance(dealership, Dealership):
                dealership = None

            before = _prepare_snapshot(entry.before)
            after = _prepare_snapshot(entry.after)

            # Write within transaction.on_commit so we don't log rolled-back changes
            def _create():
                AuditLog.objects.create(
                    company=company,
                    dealership=dealership,
                    actor_content_type=actor_ct,
                    actor_object_id=actor_id,
                    target_content_type=target_ct,
                    target_object_id=target_id,
                    action=entry.action,
                    before=before,
                    after=after,
                    ip_address=ip,
                    user_agent=ua,
                )

            transaction.on_commit(_create)

        for e in entries:
            _write_one(e)

    def _write_security_event(self, request: HttpRequest, *, status_code: int, deny_code: t.Optional[str], attempted_action: t.Optional[str]) -> None:
        """WRITE A COMPACT SECURITY/ACCESS EVENT TARGETED AT THE COMPANY (NO before/after)."""
        ctx: AuditContext = getattr(request, "_audit_ctx", AuditContext())
        company = ctx.company or None
        if not company:
            return  # cannot write without company

        actor = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
        actor_ct, actor_id = _content_type_and_id(actor)
        target_ct, target_id = _content_type_and_id(company)

        ip = _get_ip(request)
        ua = _get_user_agent(request)

        after = {"status": status_code}
        if deny_code:
            after["deny_code"] = deny_code
        if attempted_action:
            after["attempted_action"] = attempted_action

        def _create():
            AuditLog.objects.create(
                company=company,
                dealership=ctx.dealership,
                actor_content_type=actor_ct,
                actor_object_id=actor_id,
                target_content_type=target_ct,
                target_object_id=target_id,
                action=AuditAction.OTHER,  # YOU CAN ADD A DEDICATED DENIED ACTION LATER
                before=None,
                after=after,
                ip_address=ip,
                user_agent=ua,
            )

        transaction.on_commit(_create)
