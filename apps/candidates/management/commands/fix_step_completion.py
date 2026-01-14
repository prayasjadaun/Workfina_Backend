from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.candidates.models import Candidate
from apps.notifications.models import ProfileStepReminder


class Command(BaseCommand):
    help = 'Fix step completion tracking for existing candidates'

    def handle(self, *args, **options):
        candidates = Candidate.objects.all()
        fixed_count = 0

        for candidate in candidates:
            updated = False

            # If profile_step >= 1 and step1_completed is False, fix it
            if candidate.profile_step >= 1 and not candidate.step1_completed:
                candidate.step1_completed = True
                candidate.step1_completed_at = candidate.updated_at or timezone.now()
                updated = True
                self.stdout.write(f"Fixed step1 for {candidate.user.email}")

            # If profile_step >= 2 and step2_completed is False, fix it
            if candidate.profile_step >= 2 and not candidate.step2_completed:
                candidate.step2_completed = True
                candidate.step2_completed_at = candidate.updated_at or timezone.now()
                updated = True
                self.stdout.write(f"Fixed step2 for {candidate.user.email}")

            # If profile_step >= 3 and step3_completed is False, fix it
            if candidate.profile_step >= 3 and not candidate.step3_completed:
                candidate.step3_completed = True
                candidate.step3_completed_at = candidate.updated_at or timezone.now()
                updated = True
                self.stdout.write(f"Fixed step3 for {candidate.user.email}")

            # If profile_step >= 4 or is_profile_completed and step4_completed is False, fix it
            if (candidate.profile_step >= 4 or candidate.is_profile_completed) and not candidate.step4_completed:
                candidate.step4_completed = True
                candidate.step4_completed_at = candidate.updated_at or timezone.now()
                updated = True
                self.stdout.write(f"Fixed step4 for {candidate.user.email}")

            if updated:
                candidate.save()
                fixed_count += 1

        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} candidates"))