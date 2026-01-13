from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import logging

from notifications.models import ProfileStepReminder, UserNotification, NotificationLog
from notifications.services import WorkfinaFCMService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send scheduled notifications and profile reminders'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['reminders', 'scheduled', 'all'],
            default='all',
            help='Type of notifications to process'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )
    
    def handle(self, *args, **options):
        notification_type = options['type']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No notifications will be sent'))
        
        total_sent = 0
        
        # Process profile step reminders
        if notification_type in ['reminders', 'all']:
            reminder_count = self.process_profile_reminders(dry_run)
            total_sent += reminder_count
            self.stdout.write(f'Profile reminders processed: {reminder_count}')
        
        # Process scheduled notifications
        if notification_type in ['scheduled', 'all']:
            scheduled_count = self.process_scheduled_notifications(dry_run)
            total_sent += scheduled_count
            self.stdout.write(f'Scheduled notifications processed: {scheduled_count}')
        
        # Cleanup old notifications (older than 90 days)
        if not dry_run:
            cleanup_count = self.cleanup_old_notifications()
            self.stdout.write(f'Old notifications cleaned up: {cleanup_count}')
        
        self.stdout.write(
            self.style.SUCCESS(f'Notification processing completed. Total sent: {total_sent}')
        )
    
    def process_profile_reminders(self, dry_run=False):
        """Process profile completion reminders"""
        sent_count = 0
        
        # Get all users who need reminders
        reminders = ProfileStepReminder.objects.filter(is_profile_completed=False)
        
        for reminder in reminders:
            needs_reminder, reminder_type = reminder.needs_reminder()
            
            if needs_reminder:
                if dry_run:
                    self.stdout.write(
                        f'Would send {reminder_type} reminder to {reminder.user.email} (step {reminder.current_step})'
                    )
                else:
                    try:
                        result = WorkfinaFCMService.send_profile_step_reminder(
                            user=reminder.user,
                            current_step=reminder.current_step,
                            reminder_type=reminder_type
                        )
                        
                        if result.get('success'):
                            sent_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Sent {reminder_type} reminder to {reminder.user.email}'
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Failed to send reminder to {reminder.user.email}: {result.get("error")}'
                                )
                            )
                        
                        # Log the activity
                        NotificationLog.objects.create(
                            log_type='REMINDER_SCHEDULED',
                            user=reminder.user,
                            message=f'Profile step reminder ({reminder_type}) sent to step {reminder.current_step}',
                            metadata={'reminder_type': reminder_type, 'step': reminder.current_step}
                        )
                        
                    except Exception as e:
                        logger.error(f'Error sending reminder to {reminder.user.email}: {str(e)}')
                        self.stdout.write(
                            self.style.ERROR(f'Error sending reminder to {reminder.user.email}: {str(e)}')
                        )
        
        return sent_count
    
    def process_scheduled_notifications(self, dry_run=False):
        """Process pending scheduled notifications"""
        sent_count = 0
        
        # Get notifications scheduled for now or earlier
        pending_notifications = UserNotification.objects.filter(
            status='PENDING',
            scheduled_for__lte=timezone.now()
        )
        
        for notification in pending_notifications:
            if dry_run:
                self.stdout.write(
                    f'Would send notification to {notification.user.email}: {notification.title}'
                )
            else:
                try:
                    result = WorkfinaFCMService.send_notification(notification)
                    
                    if result.get('success'):
                        sent_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Sent notification to {notification.user.email}')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Failed to send notification to {notification.user.email}: {result.get("error")}'
                            )
                        )
                
                except Exception as e:
                    logger.error(f'Error sending notification {notification.id}: {str(e)}')
                    self.stdout.write(
                        self.style.ERROR(f'Error sending notification {notification.id}: {str(e)}')
                    )
        
        return sent_count
    
    def cleanup_old_notifications(self):
        """Clean up old notifications and logs"""
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        # Delete old read notifications
        old_notifications = UserNotification.objects.filter(
            created_at__lt=ninety_days_ago,
            status='READ'
        )
        count = old_notifications.count()
        old_notifications.delete()
        
        # Delete old logs
        old_logs = NotificationLog.objects.filter(
            created_at__lt=ninety_days_ago
        )
        log_count = old_logs.count()
        old_logs.delete()
        
        self.stdout.write(f'Cleaned up {count} old notifications and {log_count} old logs')
        
        return count + log_count