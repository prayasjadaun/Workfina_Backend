from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from .models import (
    SubscriptionPlan,
    CompanySubscription,
    SubscriptionHistory
)
from .serializers import (
    SubscriptionPlanSerializer,
    CompanySubscriptionSerializer,
    CompanySubscriptionDetailSerializer,
    SubscriptionStatusSerializer,
)


class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing subscription plans
    HR users can view all active plans to choose from
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only return active plans"""
        return SubscriptionPlan.objects.filter(is_active=True).order_by('price')


class CompanySubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for HR users to view their subscriptions
    Read-only: Only admin can create/modify subscriptions
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CompanySubscriptionDetailSerializer
        return CompanySubscriptionSerializer

    def get_queryset(self):
        """
        HR users can only see their own company's subscriptions
        Superusers can see all
        """
        user = self.request.user

        if user.is_superuser or user.is_staff:
            return CompanySubscription.objects.all()

        # HR users see only their company's subscriptions
        if hasattr(user, 'hr_profile'):
            return CompanySubscription.objects.filter(
                hr_profile=user.hr_profile
            ).order_by('-created_at')

        return CompanySubscription.objects.none()

    @action(detail=False, methods=['get'])
    def current(self, request):
        """
        Get current active subscription for the logged-in HR user
        Endpoint: GET /api/subscriptions/subscriptions/current/
        """
        user = request.user

        if not hasattr(user, 'hr_profile'):
            return Response({
                'error': 'HR profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get active subscription
        subscription = CompanySubscription.objects.filter(
            hr_profile=user.hr_profile,
            status='ACTIVE'
        ).first()

        if subscription:
            serializer = CompanySubscriptionDetailSerializer(subscription)
            return Response(serializer.data)

        return Response({
            'message': 'No active subscription found'
        }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def status(self, request):
        """
        Get quick subscription status for the logged-in HR user
        Endpoint: GET /api/subscriptions/subscriptions/status/

        Returns:
        - has_subscription: boolean
        - status: ACTIVE/PENDING/EXPIRED/CANCELLED
        - plan details
        - credits info
        - expiry info
        """
        user = request.user

        if not hasattr(user, 'hr_profile'):
            return Response({
                'has_subscription': False,
                'status': None,
                'plan': None,
                'plan_type': None,
                'expires_at': None,
                'days_remaining': None,
                'is_unlimited': False,
                'credits_used': 0,
                'credits_limit': None,
                'warning_level': None,
            })

        # Get latest subscription (active or pending)
        subscription = CompanySubscription.objects.filter(
            hr_profile=user.hr_profile
        ).exclude(
            status__in=['EXPIRED', 'CANCELLED']
        ).order_by('-created_at').first()

        if not subscription:
            # Check if there was any expired/cancelled subscription
            subscription = CompanySubscription.objects.filter(
                hr_profile=user.hr_profile
            ).order_by('-created_at').first()

        if subscription:
            data = {
                'has_subscription': True,
                'status': subscription.status,
                'plan': subscription.plan.name,
                'plan_type': subscription.plan.get_plan_type_display(),
                'expires_at': subscription.end_date,
                'days_remaining': subscription.days_until_expiry(),
                'is_unlimited': subscription.plan.is_unlimited,
                'credits_used': subscription.credits_used,
                'credits_limit': subscription.plan.credits_limit,
                'warning_level': subscription.get_expiry_warning_level(),
            }
        else:
            data = {
                'has_subscription': False,
                'status': None,
                'plan': None,
                'plan_type': None,
                'expires_at': None,
                'days_remaining': None,
                'is_unlimited': False,
                'credits_used': 0,
                'credits_limit': None,
                'warning_level': None,
            }

        serializer = SubscriptionStatusSerializer(data)
        return Response(serializer.data)
