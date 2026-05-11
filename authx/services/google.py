# authx/services/google.py

from __future__ import annotations

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from authx.models import AuthProvider, UserProvider


GOOGLE_ISSUERS = {
    "accounts.google.com",
    "https://accounts.google.com",
}


def verify_google_id_token(id_token: str) -> dict:
    client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")

    if not client_id:
        raise RuntimeError("Missing settings.GOOGLE_CLIENT_ID")

    payload = google_id_token.verify_oauth2_token(
        id_token,
        google_requests.Request(),
        audience=client_id,
    )

    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise ValueError("Invalid Google token issuer.")

    if payload.get("email_verified") is False:
        raise ValueError("Google email is not verified.")

    return payload


def ensure_google_provider(user, provider_uid: str):
    provider, created = UserProvider.objects.get_or_create(
        user=user,
        provider=AuthProvider.GOOGLE,
        defaults={"provider_uid": provider_uid},
    )

    if not created and provider.provider_uid != provider_uid:
        provider.provider_uid = provider_uid
        provider.save(update_fields=["provider_uid", "updated_at"])

    return provider