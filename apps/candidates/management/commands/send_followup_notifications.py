from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.candidates.models import CandidateFollowup
from apps.notifications.models import UserNotification, NotificationTemplate, NotificationLog
from server.fcm_utils import SimpleFCM
from datetime import timedelta


class Command(BaseCommand):
    help = 'Send notifications for upcoming follow-ups (checks every 15 minutes)'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        # Check for follow-ups in the next 15 minutes
        upcoming_time = now + timedelta(minutes=15)

        # Get all incomplete follow-ups that are due within the next 15 minutes
        followups = CandidateFollowup.objects.filter(
            is_completed=False,
            followup_date__lte=upcoming_time,
            followup_date__gte=now
        ).select_related('hr_user', 'candidate', 'hr_user__user')

        notifications_sent = 0

        for followup in followups:
            # Check if notification was already sent for this follow-up
            existing_notification = UserNotification.objects.filter(
                user=followup.hr_user.user,
                data_payload__followup_id=str(followup.id)
            ).exists()

            if existing_notification:
                continue  # Skip if already notified

            # Format the follow-up date and time
            followup_time = followup.followup_date.strftime("%-d %B %Y at %-I:%M %p")
            candidate_name = followup.candidate.masked_name

            # Try to get template if exists
            notification_title = "Follow-up Reminder"
            notification_body = f"Follow-up reminder for {candidate_name} scheduled at {followup_time}"

            try:
                template = NotificationTemplate.objects.filter(
                    notification_type='FOLLOWUP_REMINDER',
                    is_active=True
                ).first()

                if template:
                    notification_title = template.title.format(
                        candidate_name=candidate_name,
                        followup_time=followup_time
                    )
                    notification_body = template.body.format(
                        candidate_name=candidate_name,
                        followup_time=followup_time,
                        notes=followup.notes or "No notes"
                    )
            except Exception:
                pass  # Use default title and body

            # Create notification for HR user
            notification = UserNotification.objects.create(
                user=followup.hr_user.user,
                template=template if 'template' in locals() else None,
                title=notification_title,
                body=notification_body,
                data_payload={
                    'type': 'FOLLOWUP_REMINDER',
                    'followup_id': str(followup.id),
                    'candidate_id': str(followup.candidate.id),
                    'candidate_name': candidate_name,
                    'followup_time': followup_time,
                    'notes': followup.notes
                }
            )

            # Send FCM push notification
            hr_user = followup.hr_user.user
            if hasattr(hr_user, 'fcm_token') and hr_user.fcm_token:
                result = SimpleFCM.send_to_token(
                    token=hr_user.fcm_token,
                    title=notification_title,
                    body=notification_body,
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
                else:
                    notification.status = 'FAILED'
                    notification.error_message = result.get('error', 'Unknown error')

                notification.save()

            # Create notification log
            NotificationLog.objects.create(
                log_type='REMINDER_SCHEDULED',
                user=followup.hr_user.user,
                notification=notification,
                message=f"Follow-up reminder sent to {followup.hr_user.user.email} for candidate {candidate_name}",
                metadata={
                    'followup_id': str(followup.id),
                    'candidate_id': str(followup.candidate.id)
                }
            )

            notifications_sent += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sent follow-up notification to {followup.hr_user.user.email} for {candidate_name}'
                )
            )

        if notifications_sent > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully sent {notifications_sent} follow-up notification(s)'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('No follow-up notifications to send at this time')
            )