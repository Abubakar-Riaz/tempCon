# authx/services/providers.py

from __future__ import annotations

from authx.models import AuthProvider, UserProvider


def has_provider(user, provider: AuthProvider | str) -> bool:
    return UserProvider.objects.filter(
        user=user,
        provider=provider,
    ).exists()