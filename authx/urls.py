from django.urls import path
from authx.views.signup import (
    SignupStartView,
    SignupVerifyView,
    SignupResendOtpView,
)
from authx.views.login import (
    LoginStartView,
    LoginVerifyOtpView,
    LoginResendOtpView,
    TokenRefreshView,
)
from authx.views.passwords import (
    ForgotPasswordView,
    PasswordResetConfirmView,
    PasswordResetStartView,
)
from authx.views.sessions import (
    LoginHistoryView,
    LogoutView,
    SessionListView,
    SessionRevokeAllView,
    SessionRevokeView,
)

from authx.views.google import GoogleAuthView
from authx.views.me import MeView

urlpatterns = [
    # Signup
    path("signup/start",  SignupStartView.as_view(),   name="signup-start"),
    path("signup/verify", SignupVerifyView.as_view(),  name="signup-verify"),
    path("signup/resend", SignupResendOtpView.as_view(), name="signup-resend"),

    # Login
    path("login/start",   LoginStartView.as_view(),    name="login-start"),
    path("login/verify",  LoginVerifyOtpView.as_view(), name="login-verify"),
    path("login/resend",  LoginResendOtpView.as_view(), name="login-resend"),
    path("token/refresh", TokenRefreshView.as_view(),   name="token-refresh"),

    # Google Auth
    path("google/", GoogleAuthView.as_view(), name="authx-google"),

    # Password – forgot
    path("password/forgot/", ForgotPasswordView.as_view(), name="password-forgot"),
    path("password/reset/start/", PasswordResetStartView.as_view(), name="password-reset-start"),
    path("password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),

    path("me/", MeView.as_view(), name="authx-me"),


    path("sessions/", SessionListView.as_view(), name="authx-sessions"),
    path("sessions/revoke/", SessionRevokeView.as_view(), name="authx-sessions-revoke"),
    path("sessions/revoke-all/", SessionRevokeAllView.as_view(), name="authx-sessions-revoke-all"),
    path("login-history/", LoginHistoryView.as_view(), name="authx-login-history"),
    path("logout/", LogoutView.as_view(), name="authx-logout"),
]