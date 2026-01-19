from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions.utils import (
    check_expiring_subscriptions,
    expire_old_subscriptions
)


class Command(BaseCommand):
    help = 'Check subscription expiry and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--send-notifications',
            action='store_true',
            help='Send notifications for expiring subscriptions',
        )
        parser.add_argument(
            '--expire-old',
            action='store_true',
            help='Mark old subscriptions as expired',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Perform all checks (notifications + expiry)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Subscription Check Started at {timezone.now()} ===\n'
            )
        )

        notifications_sent = 0
        expired_count = 0

        # Send expiry notifications
        if options['send_notifications'] or options['all']:
            self.stdout.write('Checking for expiring subscriptions...')
            notifications_sent = check_expiring_subscriptions()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Created {notifications_sent} expiry notification(s)'
                )
            )

        # Expire old subscriptions
        if options['expire_old'] or options['all']:
            self.stdout.write('\nChecking for expired subscriptions...')
            expired_count = expire_old_subscriptions()
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Marked {expired_count} subscription(s) as expired'
                )
            )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n=== Subscription Check Completed ===\n'
                f'Notifications created: {notifications_sent}\n'
                f'Subscriptions expired: {expired_count}\n'
            )
        )

        if not (options['send_notifications'] or options['expire_old'] or options['all']):
            self.stdout.write(
                self.style.WARNING(
                    '\nNo action specified. Use --all, --send-notifications, or --expire-old'
                )
            )
            self.stdout.write('\nExample usage:')
            self.stdout.write('  python manage.py check_subscriptions --all')
            self.stdout.write('  python manage.py check_subscriptions --send-notifications')
            self.stdout.write('  python manage.py check_subscriptions --expire-old')
