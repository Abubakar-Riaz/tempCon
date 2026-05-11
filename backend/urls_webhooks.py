from django.urls import include, path

urlpatterns = [
    path("", include("webhooks.urls")),
]