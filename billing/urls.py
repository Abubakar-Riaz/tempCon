from django.urls import path

from billing.views import (
    BillingCheckoutSessionView,
    BillingInvoiceListView,
    BillingOverviewView,
    BillingPlansView,
    BillingPortalSessionView,
    PromotionFeaturedCardView,
)

urlpatterns = [
    path("plans/", BillingPlansView.as_view(), name="plans"),
    path("overview/", BillingOverviewView.as_view(), name="overview"),
    path("checkout-session/", BillingCheckoutSessionView.as_view(), name="checkout-session"),
    path("portal-session/", BillingPortalSessionView.as_view(), name="portal-session"),
    path("invoices/", BillingInvoiceListView.as_view(), name="billing-invoice-list"),
    path("promotion/featured-card/", PromotionFeaturedCardView.as_view(), name="promotion-featured-card"),
]