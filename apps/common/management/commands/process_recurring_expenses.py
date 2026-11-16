from django.core.management.base import BaseCommand
from apps.finance.models import RecurringExpense


class Command(BaseCommand):
    help = "Generate due expense transactions for all active recurring bills"

    def handle(self, *args, **kwargs):
        total_created = 0
        for rec in RecurringExpense.objects.filter(is_active=True):
            total_created += rec.generate_due_expenses()
        self.stdout.write(self.style.SUCCESS(f"Processed recurring bills: {total_created} expense(s) generated."))