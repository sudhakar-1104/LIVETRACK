from decimal import Decimal
from django import forms
from django.db.models import Q
from .models import Budget
from apps.finance.models import ExpenseCategory


class BudgetForm(forms.ModelForm):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Budget
        fields = ['year', 'month', 'category', 'amount']
        widgets = {
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2100}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['category'].queryset = ExpenseCategory.objects.filter(
                Q(user__isnull=True) | Q(user=user),
                active=True
            )
        self.fields['category'].empty_label = "Overall Monthly Budget (All Categories)"

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= Decimal('0.00'):
            raise forms.ValidationError("Budget amount must be greater than ₹0.00.")
        return amount