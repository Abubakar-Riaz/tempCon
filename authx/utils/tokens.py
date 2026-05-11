# authx/utils/tokens.py

from __future__ import annotations

from datetime import timedelta
from typing import Tuple

from django.conf import settings
from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken


ACCESS_COOKIE_NAME = getattr(settings, "ACCESS_COOKIE_NAME", "auth_at")
REFRESH_COOKIE_NAME = getattr(settings, "REFRESH_COOKIE_NAME", "auth_rt")

AUTH_COOKIE_PATH = getattr(settings, "AUTH_COOKIE_PATH", "/")
REFRESH_COOKIE_PATH = getattr(settings, "REFRESH_COOKIE_PATH", "/auth/token/refresh/")

AUTH_COOKIE_SAMESITE = getattr(settings, "AUTH_COOKIE_SAMESITE", "Lax")
AUTH_COOKIE_SECURE = getattr(settings, "AUTH_COOKIE_SECURE", not settings.DEBUG)

ACCESS_COOKIE_MAX_AGE = getattr(
    settings,
    "ACCESS_COOKIE_MAX_AGE",
    int(timedelta(minutes=15).total_seconds()),
)

REFRESH_COOKIE_MAX_AGE = getattr(
    settings,
    "REFRESH_COOKIE_MAX_AGE",
    int(timedelta(days=14).total_seconds()),
)


def issue_tokens(user) -> Tuple[str, str]:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token), str(refresh)


def set_auth_cookies(
    response: HttpResponse,
    *,
    access: str,
    refresh: str,
) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=ACCESS_COOKIE_MAX_AGE,
        path=AUTH_COOKIE_PATH,
    )

    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        max_age=REFRESH_COOKIE_MAX_AGE,
        path=AUTH_COOKIE_PATH,
    )


def clear_auth_cookies(response: HttpResponse) -> None:
    response.delete_cookie(
        ACCESS_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        samesite=AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=AUTH_COOKIE_PATH,
        samesite=AUTH_COOKIE_SAMESITE,
    )


def get_refresh_from_request(request: Request) -> str | None:
    return request.COOKIES.get(REFRESH_COOKIE_NAME)


def mint_rotated_tokens_from_raw(token_raw: str) -> Tuple[str, str]:
    old_refresh = RefreshToken(token_raw)
    user_id = old_refresh[jwt_settings.USER_ID_CLAIM]

    if settings.SIMPLE_JWT.get("BLACKLIST_AFTER_ROTATION", False):
        blacklist_refresh_token_safely(token_raw)

    if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False):
        new_refresh = RefreshToken()
        new_refresh[jwt_settings.USER_ID_CLAIM] = user_id
    else:
        new_refresh = old_refresh

    return str(new_refresh.access_token), str(new_refresh)


def blacklist_refresh_token_safely(token_raw: str) -> None:
    try:
        RefreshToken(token_raw).blacklist()
    except Exception:
        pass