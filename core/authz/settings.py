from django.conf import settings


AUTHZ_ENABLE_SUBSCRIPTION_CHECKS = getattr(
    settings,
    "AUTHZ_ENABLE_SUBSCRIPTION_CHECKS",
    False,
)