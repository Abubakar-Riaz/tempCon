# authx/channels_auth.py

from __future__ import annotations

import logging

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.http import parse_cookie
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

ACCESS_COOKIE_NAME = "access_token"


def extract_cookie_value(raw_cookie_header: str, cookie_name: str) -> str:
    if not raw_cookie_header:
        return ""

    try:
        cookies = parse_cookie(raw_cookie_header)
        value = cookies.get(cookie_name)

        if value:
            return value
    except Exception:
        logger.exception("Failed to parse websocket cookie header.")

    prefix = f"{cookie_name}="

    for part in raw_cookie_header.split(";"):
        part = part.strip()

        if part.startswith(prefix):
            return part[len(prefix):]

    return ""


class CookieJWTAuthMiddleware:
    def __init__(self, app):
        self.app = app
        self.jwt_authentication = JWTAuthentication()

    async def __call__(self, scope, receive, send):
        scope["user"] = await self.get_user_from_cookie(scope)
        scope["auth_error"] = None

        if not getattr(scope["user"], "is_authenticated", False):
            scope["auth_error"] = "token_expired_or_invalid"

        return await self.app(scope, receive, send)

    @database_sync_to_async
    def get_user_from_cookie(self, scope):
        headers = dict(scope.get("headers") or [])
        raw_cookie_header = headers.get(b"cookie", b"").decode("latin1")
        raw_token = extract_cookie_value(raw_cookie_header, ACCESS_COOKIE_NAME)

        if not raw_token:
            return AnonymousUser()

        try:
            validated_token = self.jwt_authentication.get_validated_token(raw_token)
            return self.jwt_authentication.get_user(validated_token)

        except (InvalidToken, TokenError):
            return AnonymousUser()

        except Exception:
            logger.exception("Unexpected websocket auth error.")
            return AnonymousUser()


def CookieJWTAuthMiddlewareStack(inner):
    return CookieJWTAuthMiddleware(inner)