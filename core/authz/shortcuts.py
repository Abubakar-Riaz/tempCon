from __future__ import annotations

from core.authz.request_context import resolve_request_dealership_context
from core.authz.resolver import build_access_context


def get_current_dealership_ctx(request):
    raw = resolve_request_dealership_context(request)

    return build_access_context(
        user=raw.user,
        membership=raw.membership,
        dealership=raw.dealership,
        subscription=raw.subscription,
    )