from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from apps.recruiters.models import HRProfile
import uuid


class SubscriptionPlan(models.Model):
    """
    Subscription plans that admin can create and manage
    """
    PLAN_TYPES = [
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly (3 Months)'),
        ('HALF_YEARLY', 'Half Yearly (6 Months)'),
        ('YEARLY', 'Yearly'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, help_text="e.g., Unlimited Monthly Plan")
    description = models.TextField(blank=True, help_text="Plan description for admin reference")
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, default='MONTHLY')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Plan price in rupees")

    # Credits configuration
    is_unlimited = models.BooleanField(default=True, help_text="If true, company gets unlimited credits")
    credits_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Monthly credit limit (leave empty for unlimited)"
    )

    # Plan status
    is_active = models.BooleanField(default=True, help_text="Only active plans can be assigned")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

    def get_duration_days(self):
        """Get plan duration in days"""
        duration_map = {
            'MONTHLY': 30,
            'QUARTERLY': 90,
            'HALF_YEARLY': 180,
            'YEARLY': 365,
        }
        return duration_map.get(self.plan_type, 30)


class CompanySubscription(models.Model):
    """
    Active subscriptions for companies
    Tracks subscription history and status
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hr_profile = models.ForeignKey(
        HRProfile,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )

    # Subscription timeline
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Credits tracking (for non-unlimited plans)
    credits_used = models.PositiveIntegerField(default=0)

    # Payment & Admin info
    payment_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Payment transaction ID or reference"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_subscriptions',
        help_text="Admin who approved this subscription"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    # Cancellation info
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_subscriptions',
        help_text="Admin who cancelled this subscription"
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # Notes
    admin_notes = models.TextField(blank=True, help_text="Internal notes for admin")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Company Subscription'
        verbose_name_plural = 'Company Subscriptions'
        indexes = [
            models.Index(fields=['status', 'end_date']),
            models.Index(fields=['hr_profile', 'status']),
        ]

    def __str__(self):
        return f"{self.hr_profile.company_name} - {self.plan.name} ({self.status})"

    def activate(self, admin_user=None):
        """Activate the subscription"""
        self.status = 'ACTIVE'
        self.start_date = timezone.now()
        self.end_date = timezone.now() + timedelta(days=self.plan.get_duration_days())
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.save()

        # Create notification via existing notification system
        from apps.notifications.models import UserNotification
        UserNotification.objects.create(
            user=self.hr_profile.user,
            title='Subscription Activated',
            body=f"Your {self.plan.name} subscription has been activated. Valid till {self.end_date.strftime('%d %b %Y')}.",
            data_payload={'type': 'subscription', 'action': 'activated', 'subscription_id': str(self.id)}
        )

    def cancel(self, admin_user=None, reason=""):
        """Cancel the subscription"""
        self.status = 'CANCELLED'
        self.cancelled_by = admin_user
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()

        # Create notification via existing notification system
        from apps.notifications.models import UserNotification
        UserNotification.objects.create(
            user=self.hr_profile.user,
            title='Subscription Cancelled',
            body=f"Your {self.plan.name} subscription has been cancelled. {reason}",
            data_payload={'type': 'subscription', 'action': 'cancelled', 'subscription_id': str(self.id)}
        )

    def mark_expired(self):
        """Mark subscription as expired"""
        self.status = 'EXPIRED'
        self.save()

        # Create notification via existing notification system
        from apps.notifications.models import UserNotification
        UserNotification.objects.create(
            user=self.hr_profile.user,
            title='Subscription Expired',
            body=f"Your {self.plan.name} subscription has expired. Please renew to continue using unlimited credits.",
            data_payload={'type': 'subscription', 'action': 'expired', 'subscription_id': str(self.id)}
        )

    def is_active(self):
        """Check if subscription is currently active"""
        if self.status != 'ACTIVE':
            return False

        if self.end_date and timezone.now() > self.end_date:
            # Auto-expire if end date passed
            self.mark_expired()
            return False

        return True

    def has_unlimited_credits(self):
        """Check if this subscription provides unlimited credits"""
        return self.is_active() and self.plan.is_unlimited

    def can_use_credits(self, amount=1):
        """Check if company can use credits"""
        if not self.is_active():
            return False

        if self.plan.is_unlimited:
            return True

        if self.plan.credits_limit:
            return (self.credits_used + amount) <= self.plan.credits_limit

        return False

    def use_credits(self, amount):
        """Use credits from subscription"""
        if self.can_use_credits(amount):
            self.credits_used += amount
            self.save()
            return True
        return False

    def days_until_expiry(self):
        """Get number of days until subscription expires"""
        if not self.end_date or self.status != 'ACTIVE':
            return None

        delta = self.end_date - timezone.now()
        return delta.days if delta.days > 0 else 0

    def get_expiry_warning_level(self):
        """Get warning level for expiry notification"""
        days = self.days_until_expiry()
        if days is None:
            return None

        if days <= 3:
            return 'CRITICAL'
        elif days <= 7:
            return 'HIGH'
        elif days <= 15:
            return 'MEDIUM'
        return 'LOW'


class SubscriptionHistory(models.Model):
    """
    Complete history of all subscription changes
    For audit trail and analytics
    """
    ACTION_TYPES = [
        ('CREATED', 'Created'),
        ('ACTIVATED', 'Activated'),
        ('RENEWED', 'Renewed'),
        ('CANCELLED', 'Cancelled'),
        ('EXPIRED', 'Expired'),
        ('MODIFIED', 'Modified'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        CompanySubscription,
        on_delete=models.CASCADE,
        related_name='history'
    )
    action = models.CharField(max_length=20, choices=ACTION_TYPES)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    details = models.JSONField(default=dict, blank=True, help_text="Additional action details")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Subscription History'
        verbose_name_plural = 'Subscription History'

    def __str__(self):
        return f"{self.subscription.hr_profile.company_name} - {self.action} at {self.created_at}"
