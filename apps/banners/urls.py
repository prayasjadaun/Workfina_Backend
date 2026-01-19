from django.urls import path
from .views import ActiveBannerView, ActiveRecruiterBannerView

urlpatterns = [
    path('active/', ActiveBannerView.as_view()),
    path('recruiter/active/', ActiveRecruiterBannerView.as_view()),
]
