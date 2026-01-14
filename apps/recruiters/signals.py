from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import HRProfile
from apps.notifications.models import UserNotification
from server.fcm_utils import SimpleFCM
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=HRProfile)
def send_verification_notification(sender, instance, **kwargs):
    """Send notification when HR/Recruiter profile is verified by admin"""
    if not instance.pk:
        return

    try:
        old_instance = HRProfile.objects.get(pk=instance.pk)

        # Check if is_verified changed from False to True
        if not old_instance.is_verified and instance.is_verified:
            user = instance.user

            title = "Profile Verified! 🎉"
            body = (
                f"Congratulations {instance.full_name or 'Recruiter'}! "
                "Your profile has been verified successfully. "
                "You can now browse and connect with qualified candidates. "
                "Start exploring talent today!"
            )

            # Create notification record
            notification = UserNotification.objects.create(
                user=user,
                title=title,
                body=body,
                data_payload={
                    'type': 'PROFILE_VERIFIED',
                    'action': 'VIEW_CANDIDATES'
                },
                status='PENDING'
            )

            # Send FCM notification if user has fcm_token
            if hasattr(user, 'fcm_token') and user.fcm_token:
                result = SimpleFCM.send_to_token(
                    token=user.fcm_token,
                    title=title,
                    body=body,
                    data={
                        'type': 'PROFILE_VERIFIED',
                        'action': 'VIEW_CANDIDATES',
                        'notification_id': str(notification.id)
                    }
                )

                if result.get('success'):
                    notification.status = 'SENT'
                    notification.fcm_message_id = result.get('message_id')
                    logger.info(f"Verification notification sent to {user.email}")
                else:
                    notification.status = 'FAILED'
                    notification.error_message = result.get('error', 'Unknown error')
                    logger.error(f"Failed to send verification notification to {user.email}")

                notification.save()
            else:
                logger.warning(f"No FCM token for user {user.email}, notification saved but not sent via FCM")

    except HRProfile.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error sending verification notification: {e}")