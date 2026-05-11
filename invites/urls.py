from django.urls import path

from .dealership_invites import (
    InviteAcceptView,
    InviteListCreateView,
    InviteResendView,
    InviteRevokeView,
)

urlpatterns = [
    path("invite/", InviteListCreateView.as_view(), name="invites-list-create"),
    path("invite/<uuid:invite_id>/resend/", InviteResendView.as_view(), name="invites-resend"),
    path("invite/<uuid:invite_id>/revoke/", InviteRevokeView.as_view(), name="invites-revoke"),
    path("invite/<str:token>/accept/", InviteAcceptView.as_view(), name="invites-accept"),
]