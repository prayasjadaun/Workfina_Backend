from django.utils import timezone
from datetime import timedelta
from .models import CompanySubscription


def check_expiring_subscriptions():
    """
    Check for subscriptions expiring soon and send notifications
    Should be run daily via cron job or celery task
    """
    from apps.notifications.models import UserNotification

    now = timezone.now()
    warning_days = [7, 3, 1]  # Send notifications at 7, 3, and 1 day before expiry
    count = 0

    for days in warning_days:
        expiry_date = now + timedelta(days=days)
        # Find subscriptions expiring in exactly N days
        expiring_subscriptions = CompanySubscription.objects.filter(
            status='ACTIVE',
            end_date__date=expiry_date.date()
        )

        for subscription in expiring_subscriptions:
            # Check if notification already sent for this milestone
            existing = UserNotification.objects.filter(
                user=subscription.hr_profile.user,
                data_payload__subscription_id=str(subscription.id),
                data_payload__days_remaining=days,
                created_at__date=now.date()
            ).exists()

            if not existing:
                UserNotification.objects.create(
                    user=subscription.hr_profile.user,
                    title='Subscription Expiring Soon',
                    body=f'Your {subscription.plan.name} subscription will expire in {days} day{"s" if days > 1 else ""} on {subscription.end_date.strftime("%d %b %Y")}. Please renew to continue.',
                    data_payload={
                        'type': 'subscription',
                        'action': 'expiring',
                        'subscription_id': str(subscription.id),
                        'days_remaining': days
                    }
                )
                count += 1

    return count


def expire_old_subscriptions():
    """
    Mark subscriptions as expired if their end date has passed
    Should be run daily via cron job or celery task
    """
    now = timezone.now()

    expired_subscriptions = CompanySubscription.objects.filter(
        status='ACTIVE',
        end_date__lt=now
    )

    count = 0
    for subscription in expired_subscriptions:
        subscription.mark_expired()
        count += 1

    return count


def get_active_subscription(hr_profile):
    """
    Get active subscription for an HR profile
    Returns the most recent active subscription or None
    """
    try:
        return CompanySubscription.objects.filter(
            hr_profile=hr_profile,
            status='ACTIVE'
        ).order_by('-created_at').first()
    except CompanySubscription.DoesNotExist:
        return None


def has_unlimited_credits(hr_profile):
    """
    Check if HR profile has unlimited credits via active subscription
    """
    subscription = get_active_subscription(hr_profile)
    if subscription:
        return subscription.has_unlimited_credits()
    return False


def can_use_credits(hr_profile, amount=1):
    """
    Check if HR profile can use credits
    Returns (can_use, reason)
    """
    subscription = get_active_subscription(hr_profile)

    if subscription:
        if subscription.can_use_credits(amount):
            return (True, "Subscription active")
        else:
            return (False, "Subscription credit limit reached")

    # No subscription, check wallet balance
    return (None, "No active subscription")


def get_subscription_status(hr_profile):
    """
    Get comprehensive subscription status for HR profile
    """
    subscription = get_active_subscription(hr_profile)

    if not subscription:
        return {
            'has_subscription': False,
            'status': None,
            'plan': None,
            'expires_at': None,
            'days_remaining': None,
            'is_unlimited': False,
            'credits_used': 0,
            'credits_limit': None
        }

    return {
        'has_subscription': True,
        'status': subscription.status,
        'plan': subscription.plan.name,
        'plan_type': subscription.plan.get_plan_type_display(),
        'expires_at': subscription.end_date,
        'days_remaining': subscription.days_until_expiry(),
        'is_unlimited': subscription.plan.is_unlimited,
        'credits_used': subscription.credits_used,
        'credits_limit': subscription.plan.credits_limit,
        'warning_level': subscription.get_expiry_warning_level()
    }


def send_test_notification(subscription_id):
    """
    Send a test notification for testing purposes
    """
    from apps.notifications.models import UserNotification

    try:
        subscription = CompanySubscription.objects.get(id=subscription_id)
        UserNotification.objects.create(
            user=subscription.hr_profile.user,
            title='Test Subscription Notification',
            body=f'This is a test notification for your {subscription.plan.name} subscription.',
            data_payload={
                'type': 'subscription',
                'action': 'test',
                'subscription_id': str(subscription.id)
            }
        )
        return True
    except CompanySubscription.DoesNotExist:
        return False
