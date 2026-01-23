from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import CompanySubscription, SubscriptionHistory


@receiver(post_save, sender=CompanySubscription)
def create_subscription_history(sender, instance, created, **kwargs):
    """
    Create history entry whenever subscription is created or updated
    """
    if created:
        # History for new subscription is already created in admin
        # This handles creation from other sources (API, scripts, etc.)
        if not instance.history.filter(action='CREATED').exists():
            company_name = instance.hr_profile.company.name if instance.hr_profile.company else "No Company"
            SubscriptionHistory.objects.create(
                subscription=instance,
                action='CREATED',
                details={
                    'plan': instance.plan.name,
                    'status': instance.status,
                    'company': company_name
                },
                notes='Subscription created'
            )


@receiver(pre_save, sender=CompanySubscription)
def track_status_changes(sender, instance, **kwargs):
    """
    Track status changes and create appropriate history entries
    Also auto-calculate end_date if missing
    """
    print(f"DEBUG pre_save: Subscription {instance.id if instance.pk else 'NEW'}")

    # Auto-calculate end_date if start_date exists but end_date is missing
    if instance.start_date and not instance.end_date:
        print(f"DEBUG: Auto-calculating end_date from start_date={instance.start_date}")
        instance.end_date = instance.start_date + timedelta(days=instance.plan.get_duration_days())
        print(f"DEBUG: Calculated end_date={instance.end_date}")

    if instance.pk:  # Only for existing subscriptions
        try:
            old_instance = CompanySubscription.objects.get(pk=instance.pk)
            print(f"DEBUG: Old status={old_instance.status}, New status={instance.status}")

            # Status changed
            if old_instance.status != instance.status:
                action_map = {
                    'ACTIVE': 'ACTIVATED',
                    'CANCELLED': 'CANCELLED',
                    'EXPIRED': 'EXPIRED',
                }

                action = action_map.get(instance.status, 'MODIFIED')

                print(f"DEBUG: Status changed! Setting _status_changed flag")
                # Store old status for notification
                instance._status_changed = True
                instance._old_status = old_instance.status
                instance._new_status = instance.status
                instance._action = action

        except CompanySubscription.DoesNotExist:
            print(f"DEBUG: Old instance not found")
            pass


@receiver(post_save, sender=CompanySubscription)
def execute_post_save_history(sender, instance, created, **kwargs):
    """
    Execute any pending post-save history creation and send notifications
    """
    print(f"DEBUG: post_save signal fired for subscription {instance.id}")
    print(f"DEBUG: created={created}, has _status_changed={hasattr(instance, '_status_changed')}")

    # Handle status changes
    if hasattr(instance, '_status_changed') and instance._status_changed:
        from apps.notifications.models import UserNotification

        print(f"DEBUG: Status changed from {instance._old_status} to {instance._new_status}")
        print(f"DEBUG: User: {instance.hr_profile.user.email}")

        # Create history entry
        SubscriptionHistory.objects.create(
            subscription=instance,
            action=instance._action,
            details={
                'old_status': instance._old_status,
                'new_status': instance._new_status,
                'changed_at': timezone.now().isoformat()
            },
            notes=f'Status changed from {instance._old_status} to {instance._new_status}'
        )

        # Send notification based on new status
        if instance._new_status == 'ACTIVE' and instance.end_date:
            print(f"DEBUG: Creating ACTIVATED notification")
            notif = UserNotification.objects.create(
                user=instance.hr_profile.user,
                title='Subscription Activated',
                body=f"Your {instance.plan.name} subscription has been activated. Valid till {instance.end_date.strftime('%d %b %Y')}.",
                data_payload={
                    'type': 'subscription',
                    'action': 'activated',
                    'subscription_id': str(instance.id)
                }
            )
            print(f"DEBUG: Notification created with ID: {notif.id}")
            # Send FCM notification
            try:
                from apps.notifications.services import WorkfinaFCMService
                print(f"DEBUG: Calling FCM service...")
                result = WorkfinaFCMService.send_notification(notif)
                print(f"DEBUG: FCM notification result: {result}")
            except Exception as e:
                print(f"DEBUG: FCM send failed with exception: {e}")
                import traceback
                traceback.print_exc()
        elif instance._new_status == 'CANCELLED':
            print(f"DEBUG: Creating CANCELLED notification")
            notif = UserNotification.objects.create(
                user=instance.hr_profile.user,
                title='Subscription Cancelled',
                body=f"Your {instance.plan.name} subscription has been cancelled.",
                data_payload={
                    'type': 'subscription',
                    'action': 'cancelled',
                    'subscription_id': str(instance.id)
                }
            )
            try:
                from apps.notifications.services import WorkfinaFCMService
                print(f"DEBUG: Calling FCM service...")
                result = WorkfinaFCMService.send_notification(notif)
                print(f"DEBUG: FCM notification result: {result}")
            except Exception as e:
                print(f"DEBUG: FCM send failed: {e}")
                import traceback
                traceback.print_exc()
        elif instance._new_status == 'EXPIRED':
            print(f"DEBUG: Creating EXPIRED notification")
            notif = UserNotification.objects.create(
                user=instance.hr_profile.user,
                title='Subscription Expired',
                body=f"Your {instance.plan.name} subscription has expired. Please renew to continue using unlimited credits.",
                data_payload={
                    'type': 'subscription',
                    'action': 'expired',
                    'subscription_id': str(instance.id)
                }
            )
            try:
                from apps.notifications.services import WorkfinaFCMService
                print(f"DEBUG: Calling FCM service...")
                result = WorkfinaFCMService.send_notification(notif)
                print(f"DEBUG: FCM notification result: {result}")
            except Exception as e:
                print(f"DEBUG: FCM send failed: {e}")
                import traceback
                traceback.print_exc()

        # Clean up
        delattr(instance, '_status_changed')
        delattr(instance, '_old_status')
        delattr(instance, '_new_status')
        delattr(instance, '_action')


@receiver(post_save, sender=CompanySubscription)
def auto_expire_subscriptions(sender, instance, **kwargs):
    """
    Automatically mark subscriptions as expired if end date has passed
    Also send expiry warnings if expiring soon
    This runs on every save, but only processes ACTIVE subscriptions
    """
    if instance.status == 'ACTIVE' and instance.end_date:
        from apps.notifications.models import UserNotification
        now = timezone.now()

        # Check if already expired
        if now > instance.end_date:
            # Avoid recursion by checking if already expired
            if instance.status == 'ACTIVE':
                instance.mark_expired()
        else:
            # Send expiry warnings
            days_remaining = (instance.end_date - now).days

            # Send notification at 7, 3, and 1 day before expiry
            if days_remaining in [7, 3, 1]:
                # Check if notification already sent for this milestone today
                notification_exists = UserNotification.objects.filter(
                    user=instance.hr_profile.user,
                    data_payload__subscription_id=str(instance.id),
                    data_payload__days_remaining=days_remaining,
                    created_at__date=now.date()
                ).exists()

                if not notification_exists:
                    notif = UserNotification.objects.create(
                        user=instance.hr_profile.user,
                        title='Subscription Expiring Soon',
                        body=f'Your {instance.plan.name} subscription will expire in {days_remaining} day{"s" if days_remaining > 1 else ""} on {instance.end_date.strftime("%d %b %Y")}. Please renew to continue.',
                        data_payload={
                            'type': 'subscription',
                            'action': 'expiring',
                            'subscription_id': str(instance.id),
                            'days_remaining': days_remaining
                        }
                    )
                    # Send FCM notification
                    try:
                        from apps.notifications.services import WorkfinaFCMService
                        WorkfinaFCMService.send_notification(notif)
                    except Exception:
                        pass


