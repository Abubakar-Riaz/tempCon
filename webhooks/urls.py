from django.urls import path

from webhooks.views.stripe import StripeWebhookView

urlpatterns = [
    path("stripe/", StripeWebhookView.as_view(), name="stripe-webhook"),
]