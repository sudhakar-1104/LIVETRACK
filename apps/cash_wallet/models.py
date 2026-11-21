from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CashInflow(models.Model):
    """Money added to your physical cash wallet (isolated from main Income)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_inflows')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    source = models.CharField(max_length=120, help_text="e.g., ATM Withdrawal, Cash Received, Opening Balance")
    entry_date = models.DateField(default=timezone.localdate)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-entry_date', '-created_at']

    def __str__(self):
        return f"+₹{self.amount} ({self.source})"


class CashSpend(models.Model):
    """Physical cash spent (isolated from main Expenses & Budgets)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_spends')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    item = models.CharField(max_length=150, help_text="e.g., Auto fare, Tea & snacks, Groceries")
    tag = models.CharField(max_length=60, blank=True, default='General', help_text="Optional label like Travel, Food, Misc")
    spend_date = models.DateField(default=timezone.localdate)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-spend_date', '-created_at']

    def __str__(self):
        return f"-₹{self.amount} ({self.item})"