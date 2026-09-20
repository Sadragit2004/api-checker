from django.urls import path

from .views import market_api

urlpatterns = [
    path(
        "market/",
        market_api,
        name="market-api",
    ),
]