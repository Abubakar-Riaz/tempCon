# authx/authentication.py

from __future__ import annotations

from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication

from authx.utils.tokens import ACCESS_COOKIE_NAME


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        raw_token = request.COOKIES.get(
            getattr(settings, "ACCESS_COOKIE_NAME", ACCESS_COOKIE_NAME)
        )

        if not raw_token:
            return None

        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)

        return user, validated_token