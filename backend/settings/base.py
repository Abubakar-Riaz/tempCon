import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = [
    "dev.buycon.com",
    "cars.buycon.com",
    "localhost",
    "127.0.0.1",
]

INSTALLED_APPS = [
    "channels",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts",
    "audit",
    "authx",
    "billing",
    "buying",
    "core",
    "hammer",
    "invites",
    "inventory",
    "inspections",
    "jobs",
    "notifications",
    "recon",
    "vendors",

]

# Add this only if you are moving to custom user model before first migration:
AUTH_USER_MODEL = "accounts.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "backend.asgi.application"
WSGI_APPLICATION = "backend.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DATABASE_NAME", "#"),
        "USER": os.environ.get("DATABASE_USER", "#"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "#"),
        "HOST": os.environ.get("DATABASE_HOST", "#"),
        "PORT": os.environ.get("DATABASE_PORT", "#"),
    }
}



AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]



REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "authx.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": SECRET_KEY,
}


CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "#",
)

CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "#",
)

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60


CHANNEL_REDIS_URL = "redis://127.0.0.1:6379/2"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CHANNEL_REDIS_URL],
        },
    },
}


SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

REFRESH_COOKIE_NAME = "buycon_rt"
REFRESH_COOKIE_PATH = "/backend/api/v1/accounts/auth/"
REFRESH_COOKIE_SECURE = True
REFRESH_COOKIE_SAMESITE = "None"

FRONTEND_URL = os.environ.get("FRONTEND_URL", "#").strip()


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "#").strip()

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "#").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "#").strip()

CHECKOUT_SUCCESS_URL = os.environ.get(
    "CHECKOUT_SUCCESS_URL",
    "#",
).strip()
CHECKOUT_CANCEL_URL = os.environ.get(
    "CHECKOUT_CANCEL_URL",
    "#",
).strip()
BILLING_PORTAL_RETURN_URL = os.environ.get(
    "BILLING_PORTAL_RETURN_URL",
    "#",
).strip()

STRIPE_PRICE_ID_BASIC = os.environ.get("STRIPE_PRICE_ID_BASIC", "#").strip()
TRIAL_DAYS_BASIC = int(os.environ.get("TRIAL_DAYS_BASIC", "#"))

ALLOWED_PRICE_IDS = [
    p.strip()
    for p in os.environ.get("ALLOWED_PRICE_IDS", "#").split(",")
    if p.strip()
]

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "#").strip()
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "#").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "#").strip()
EMAIL_SANDBOX_MODE = os.environ.get("EMAIL_SANDBOX_MODE", '#').lower() == "true"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

STATIC_URL = "/backend/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/backend/media/"
MEDIA_ROOT = "/var/www/buycon/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"