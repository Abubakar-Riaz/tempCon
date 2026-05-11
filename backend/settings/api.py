from corsheaders.defaults import default_headers
from .base import *  # noqa

ROOT_URLCONF = "backend.urls_api"

FORCE_SCRIPT_NAME = "/backend"

CORS_ALLOWED_ORIGINS = [
    "https://dev.buycon.com",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-company-id",
    "x-dealership-id",
]

CSRF_TRUSTED_ORIGINS = [
    "https://dev.buycon.com",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]