from django.core.management.base import BaseCommand
from apps.tasks.models import TaskCategory
from apps.finance.models import ExpenseCategory, PaymentMethod, CurrencyRate
from decimal import Decimal

class Command(BaseCommand):
    help = "Seed default task categories, expense categories, and payment methods"

    def handle(self, *args, **kwargs):
        task_cats = ['Work', 'Personal', 'Health & Fitness', 'Finance', 'Learning', 'Errands']
        expense_cats = [
            'Food & Dining', 'Groceries', 'Transport & Fuel', 'Rent & Utilities',
            'Shopping', 'Healthcare', 'Entertainment', 'Subscriptions', 'Education', 'Other'
        ]

        currencies = [
            ('INR', '₹', 'Indian Rupee', Decimal('1.0000')),
            ('USD', '$', 'US Dollar', Decimal('84.5000')),
            ('EUR', '€', 'Euro', Decimal('91.0000')),
            ('GBP', '£', 'British Pound', Decimal('107.0000')),
            ('AED', 'AED', 'UAE Dirham', Decimal('23.0000')),
            ('SGD', 'S$', 'Singapore Dollar', Decimal('63.0000')),
        ]
        for code, symbol, name, rate in currencies:
            CurrencyRate.objects.get_or_create(
                user=None, code=code,
                defaults={'symbol': symbol, 'name': name, 'rate_to_base': rate}
            )
        pay_methods = ['UPI', 'Cash', 'Debit Card', 'Credit Card', 'Bank Transfer']

        for name in task_cats:
            TaskCategory.objects.get_or_create(user=None, name=name)

        for name in expense_cats:
            ExpenseCategory.objects.get_or_create(user=None, name=name)

        for name in pay_methods:
            PaymentMethod.objects.get_or_create(user=None, name=name)

        self.stdout.write(self.style.SUCCESS("Default categories and payment methods seeded successfully!"))