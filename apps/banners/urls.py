from django.urls import path
from .views import ActiveBannerView

urlpatterns = [
    path('active/', ActiveBannerView.as_view()),
]
