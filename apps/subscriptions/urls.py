from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet,
    CompanySubscriptionViewSet,
)

router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet, basename='subscription-plan')
router.register(r'subscriptions', CompanySubscriptionViewSet, basename='company-subscription')

urlpatterns = [
    path('', include(router.urls)),
]
