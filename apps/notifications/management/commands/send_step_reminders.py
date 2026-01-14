from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import StepNotificationDetail, UserNotification, NotificationLog
from apps.candidates.models import Candidate
from datetime import timedelta


class Command(BaseCommand):
    help = 'Send step-wise reminders to candidates who haven\'t completed their profile'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        reminders_sent = 0

        # Get all incomplete candidate profiles
        incomplete_candidates = Candidate.objects.filter(
            is_profile_completed=False,
            user__role='candidate'
        ).select_related('user', 'user__step_reminder')

        for candidate in incomplete_candidates:
            # Get ProfileStepReminder for tracking
            try:
                reminder = candidate.user.step_reminder
            except:
                continue

            # Check each step and send reminder if needed
            steps_to_check = [
                (1, candidate.step1_completed, reminder.step1_reminder_sent, candidate.created_at),
                (2, candidate.step2_completed, reminder.step2_reminder_sent, candidate.step1_completed_at or candidate.created_at),
                (3, candidate.step3_completed, reminder.step3_reminder_sent, candidate.step2_completed_at or candidate.created_at),
                (4, candidate.step4_completed, reminder.step4_reminder_sent, candidate.step3_completed_at or candidate.created_at),
            ]

            for step_num, is_completed, reminder_sent, last_action_time in steps_to_check:
                # Skip if already completed or reminder already sent
                if is_completed or reminder_sent:
                    continue

                # Get step notification details
                try:
                    step_detail = StepNotificationDetail.objects.get(
                        step_number=step_num,
                        is_active=True
                    )
                except StepNotificationDetail.DoesNotExist:
                    continue

                # Check if enough time has passed since last action
                time_elapsed = now - last_action_time
                required_delay = timedelta(hours=step_detail.delay_hours)

                if time_elapsed >= required_delay:
                    # Send notification to CANDIDATE
                    notification = UserNotification.objects.create(
                        user=candidate.user,
                        title=step_detail.heading,
                        body=step_detail.description,
                        data_payload={
                            'type': 'PROFILE_STEP_REMINDER',
                            'step_number': step_num,
                            'heading': step_detail.heading,
                            'description': step_detail.description
                        }
                    )

                    # Mark reminder as sent in ProfileStepReminder
                    if step_num == 1:
                        reminder.step1_reminder_sent = True
                    elif step_num == 2:
                        reminder.step2_reminder_sent = True
                    elif step_num == 3:
                        reminder.step3_reminder_sent = True
                    elif step_num == 4:
                        reminder.step4_reminder_sent = True

                    reminder.save()

                    # Create log
                    NotificationLog.objects.create(
                        log_type='REMINDER_SCHEDULED',
                        user=candidate.user,
                        notification=notification,
                        message=f"Step {step_num} reminder sent to {candidate.user.email}: {step_detail.heading}",
                        metadata={
                            'step_number': step_num,
                            'delay_hours': step_detail.delay_hours,
                            'candidate_id': str(candidate.id)
                        }
                    )

                    reminders_sent += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Sent step {step_num} reminder to {candidate.user.email}'
                        )
                    )

        if reminders_sent > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully sent {reminders_sent} step reminder(s)'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('No step reminders to send at this time')
            )