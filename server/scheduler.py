from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def get_scheduler():
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(
            jobstores={'default': MemoryJobStore()},
            timezone='Asia/Kolkata'
        )
        scheduler.start()
        logger.info("APScheduler started")
    return scheduler


def send_followup_notification(followup_id):
    """Send notification for a specific followup"""
    from apps.candidates.models import CandidateFollowup
    from apps.notifications.models import UserNotification, NotificationLog
    from server.fcm_utils import SimpleFCM

    try:
        followup = CandidateFollowup.objects.select_related(
            'hr_user', 'hr_user__user', 'candidate'
        ).get(id=followup_id, is_completed=False)

        hr_user = followup.hr_user.user
        candidate_name = f"{followup.candidate.first_name} {followup.candidate.last_name}"
        # Convert to IST for display
        import pytz
        ist = pytz.timezone('Asia/Kolkata')
        followup_time_ist = followup.followup_date.astimezone(ist)
        followup_time = followup_time_ist.strftime("%-I:%M %p")

        title = "Follow-up Reminder"
        body = f"Reminder: Follow-up with {candidate_name} in 5 minutes at {followup_time}"

        # Create notification record
        notification = UserNotification.objects.create(
            user=hr_user,
            title=title,
            body=body,
            data_payload={
                'type': 'FOLLOWUP_REMINDER',
                'followup_id': str(followup.id),
                'candidate_id': str(followup.candidate.id),
                'candidate_name': candidate_name
            },
            status='PENDING'
        )

        # Send FCM push notification
        if hasattr(hr_user, 'fcm_token') and hr_user.fcm_token:
            result = SimpleFCM.send_to_token(
                token=hr_user.fcm_token,
                title=title,
                body=body,
                data={
                    'type': 'FOLLOWUP_REMINDER',
                    'followup_id': str(followup.id),
                    'candidate_id': str(followup.candidate.id),
                    'notification_id': str(notification.id)
                }
            )

            if result.get('success'):
                notification.status = 'SENT'
                notification.fcm_message_id = result.get('message_id')
                logger.info(f"Followup notification sent to {hr_user.email}")
            else:
                notification.status = 'FAILED'
                notification.error_message = result.get('error', 'Unknown error')
                logger.error(f"Failed to send followup notification: {result.get('error')}")

            notification.save()

        # Log the notification
        NotificationLog.objects.create(
            log_type='REMINDER_SCHEDULED',
            user=hr_user,
            notification=notification,
            message=f"Followup reminder sent for {candidate_name}",
            metadata={'followup_id': str(followup.id)}
        )

    except CandidateFollowup.DoesNotExist:
        logger.warning(f"Followup {followup_id} not found or already completed")
    except Exception as e:
        logger.error(f"Error sending followup notification: {e}")


def schedule_followup_notification(followup):
    """Schedule a notification 5 minutes before followup time"""
    sched = get_scheduler()

    # Calculate notification time (5 min before followup)
    notify_time = followup.followup_date - timedelta(minutes=5)

    # Don't schedule if time has already passed
    if notify_time <= timezone.now():
        logger.warning(f"Followup time already passed for {followup.id}")
        return

    job_id = f"followup_{followup.id}"

    # Remove existing job if any (for updates)
    try:
        sched.remove_job(job_id)
    except:
        pass

    # Schedule new job
    sched.add_job(
        send_followup_notification,
        'date',
        run_date=notify_time,
        args=[followup.id],
        id=job_id,
        replace_existing=True
    )

    logger.info(f"Scheduled notification for followup {followup.id} at {notify_time}")


def cancel_followup_notification(followup_id):
    """Cancel scheduled notification for a followup"""
    sched = get_scheduler()
    job_id = f"followup_{followup_id}"

    try:
        sched.remove_job(job_id)
        logger.info(f"Cancelled notification for followup {followup_id}")
    except:
        pass
