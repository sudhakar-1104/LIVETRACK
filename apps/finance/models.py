from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from apps.common.models import TimeStampedModel
import calendar
from datetime import timedelta
from django.utils import timezone

def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)


class ExpenseCategory(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='expense_categories'
    )
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class PaymentMethod(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment_methods'
    )
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Expense(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    expense_date = models.DateField()
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'expense_date']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        return f"{self.description} - ₹{self.amount}"

    currency = models.CharField(max_length=10, default='INR')
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))]
    )


class Income(TimeStampedModel):
    SOURCE_CHOICES = [
        ('SALARY', 'Salary'),
        ('FREELANCE', 'Freelance / Business'),
        ('BONUS', 'Bonus / Incentive'),
        ('REFUND', 'Refund / Cashback'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='incomes'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    income_date = models.DateField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='SALARY')
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-income_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'income_date']),
        ]

    def __str__(self):
        return f"{self.get_source_display()} - ₹{self.amount}"

    currency = models.CharField(max_length=10, default='INR')
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))]
    )


class RecurringExpense(TimeStampedModel):
    FREQUENCY_CHOICES = [
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
        ('QUARTERLY', 'Quarterly'),
        ('YEARLY', 'Yearly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recurring_expenses'
    )
    description = models.CharField(max_length=255)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='recurring_expenses'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='recurring_expenses'
    )
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES, default='MONTHLY')
    start_date = models.DateField()
    next_due_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_generated_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['next_due_date', 'description']
        indexes = [
            models.Index(fields=['user', 'is_active', 'next_due_date']),
        ]

    def calculate_next_date(self, from_date):
        if self.frequency == 'WEEKLY':
            return from_date + timedelta(weeks=1)
        elif self.frequency == 'MONTHLY':
            return add_months(from_date, 1)
        elif self.frequency == 'QUARTERLY':
            return add_months(from_date, 3)
        elif self.frequency == 'YEARLY':
            return add_months(from_date, 12)
        return from_date

    def generate_due_expenses(self, up_to_date=None):
        """Generate Expense entries for all due dates up to up_to_date without duplicates."""
        if not self.is_active:
            return 0
        target_date = up_to_date or timezone.localdate()
        created_count = 0

        while self.is_active and self.next_due_date <= target_date:
            if self.end_date and self.next_due_date > self.end_date:
                self.is_active = False
                break

            due_dt = self.next_due_date
            if self.last_generated_date != due_dt:
                Expense.objects.create(
                    user=self.user,
                    amount=self.amount,
                    expense_date=due_dt,
                    category=self.category,
                    payment_method=self.payment_method,
                    description=f"{self.description} (Recurring)",
                    notes=self.notes,
                )
                self.last_generated_date = due_dt
                created_count += 1

            following_dt = self.calculate_next_date(due_dt)
            if self.end_date and following_dt > self.end_date:
                self.next_due_date = following_dt
                self.is_active = False
                break
            self.next_due_date = following_dt

        self.save()
        return created_count

    def __str__(self):
        return f"{self.description} - ₹{self.amount} ({self.get_frequency_display()})"

    currency = models.CharField(max_length=10, default='INR')
    original_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    exchange_rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))]
    )



class CurrencyRate(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='currency_rates'
    )
    code = models.CharField(max_length=10)       # e.g., INR, USD, EUR, GBP, AED, SGD
    symbol = models.CharField(max_length=5)      # e.g., ₹, $, €, £
    name = models.CharField(max_length=50)
    rate_to_base = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('1.0000'),
        validators=[MinValueValidator(Decimal('0.0001'))],
        help_text="1 unit of this currency in base reporting currency (INR)."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} ({self.symbol}) — 1 {self.code} = ₹{self.rate_to_base}"