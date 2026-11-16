from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from apps.common.models import TimeStampedModel
from apps.finance.models import ExpenseCategory


class Budget(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    year = models.PositiveIntegerField()
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='budgets',
        help_text="Leave blank for overall monthly budget."
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    class Meta:
        ordering = ['-year', '-month', 'category__name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'year', 'month', 'category'],
                name='unique_category_budget_per_month'
            ),
            models.UniqueConstraint(
                fields=['user', 'year', 'month'],
                condition=models.Q(category__isnull=True),
                name='unique_overall_budget_per_month'
            ),
        ]

    def __str__(self):
        target = self.category.name if self.category else "Overall Budget"
        return f"{self.year}-{self.month:02d} | {target}: ₹{self.amount}"