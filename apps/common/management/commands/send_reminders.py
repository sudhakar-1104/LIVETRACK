from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from apps.common.reminders import sync_user_reminders

User = get_user_model()


class Command(BaseCommand):
    help = "Generate in-app and email reminders for all active users"

    def handle(self, *args, **kwargs):
        total = 0
        for user in User.objects.filter(is_active=True):
            total += len(sync_user_reminders(user, send_email=True))
        self.stdout.write(self.style.SUCCESS(f"Reminder check complete: {total} new alert(s) generated."))