from decimal import Decimal
from django import forms
from django.db.models import Q
from django.utils import timezone
from .models import (
    CurrencyRate,
    Expense,
    ExpenseCategory,
    Income,
    PaymentMethod,
    RecurringExpense,
)
from apps.tasks.models import TaskCategory


def _get_currency_choices(user):
    qs = CurrencyRate.objects.filter(Q(user__isnull=True) | Q(user=user), is_active=True)
    choices = []
    seen = set()
    for c in qs:
        if c.code not in seen:
            choices.append((c.code, f"{c.code} ({c.symbol})"))
            seen.add(c.code)
    return choices or [('INR', 'INR (₹)')]


class ExpenseForm(forms.ModelForm):
    currency = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'})
    )

    class Meta:
        model = Expense
        fields = [
            'original_amount', 'currency', 'exchange_rate',
            'expense_date', 'category', 'payment_method', 'description', 'notes'
        ]
        labels = {
            'original_amount': 'Amount',
            'exchange_rate': 'Exchange Rate to INR (1.0000 for INR)',
        }
        widgets = {
            'original_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0.0001', 'id': 'id_exchange_rate'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Merchant or item description'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].choices = _get_currency_choices(user)
        if self.instance.pk and self.instance.original_amount is None:
            self.fields['original_amount'].initial = self.instance.amount
        if not self.instance.pk:
            self.fields['expense_date'].initial = timezone.localdate()
        if user is not None:
            self.fields['category'].queryset = ExpenseCategory.objects.filter(
                Q(user__isnull=True) | Q(user=user), active=True
            )
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                Q(user__isnull=True) | Q(user=user), active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        orig = cleaned_data.get('original_amount')
        currency = cleaned_data.get('currency', 'INR')
        rate = cleaned_data.get('exchange_rate') or Decimal('1.0000')
        if currency == 'INR':
            rate = Decimal('1.0000')
            cleaned_data['exchange_rate'] = rate
        if orig is None or orig <= Decimal('0.00'):
            raise forms.ValidationError("Amount must be greater than 0.00.")
        if rate <= Decimal('0.0000'):
            raise forms.ValidationError("Exchange rate must be greater than 0.")
        self.instance.amount = (orig * rate).quantize(Decimal('0.01'))
        return cleaned_data


class IncomeForm(forms.ModelForm):
    currency = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'})
    )

    class Meta:
        model = Income
        fields = [
            'original_amount', 'currency', 'exchange_rate',
            'income_date', 'source', 'description', 'notes'
        ]
        labels = {
            'original_amount': 'Amount',
            'exchange_rate': 'Exchange Rate to INR (1.0000 for INR)',
        }
        widgets = {
            'original_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0.0001', 'id': 'id_exchange_rate'}),
            'income_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Monthly Salary, Project Payout'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes...'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].choices = _get_currency_choices(user)
        if self.instance.pk and self.instance.original_amount is None:
            self.fields['original_amount'].initial = self.instance.amount
        if not self.instance.pk:
            self.fields['income_date'].initial = timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()
        orig = cleaned_data.get('original_amount')
        currency = cleaned_data.get('currency', 'INR')
        rate = cleaned_data.get('exchange_rate') or Decimal('1.0000')
        if currency == 'INR':
            rate = Decimal('1.0000')
            cleaned_data['exchange_rate'] = rate
        if orig is None or orig <= Decimal('0.00'):
            raise forms.ValidationError("Income amount must be greater than 0.00.")
        if rate <= Decimal('0.0000'):
            raise forms.ValidationError("Exchange rate must be greater than 0.")
        self.instance.amount = (orig * rate).quantize(Decimal('0.01'))
        return cleaned_data


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model = ExpenseCategory
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'New expense category'})}


class PaymentMethodForm(forms.ModelForm):
    class Meta:
        model = PaymentMethod
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'New payment method'})}


class TaskCategoryForm(forms.ModelForm):
    class Meta:
        model = TaskCategory
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'New task category'})}


class RecurringExpenseForm(forms.ModelForm):
    currency = forms.ChoiceField(
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_currency'})
    )

    class Meta:
        model = RecurringExpense
        fields = [
            'description', 'original_amount', 'currency', 'exchange_rate',
            'category', 'payment_method', 'frequency', 'start_date', 'end_date', 'notes'
        ]
        labels = {
            'original_amount': 'Amount',
            'exchange_rate': 'Exchange Rate to INR (1.0000 for INR)',
        }
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., House Rent, Broadband, Netflix'}),
            'original_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'exchange_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001', 'min': '0.0001', 'id': 'id_exchange_rate'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'frequency': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional bill details...'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['currency'].choices = _get_currency_choices(user)
        if self.instance.pk and self.instance.original_amount is None:
            self.fields['original_amount'].initial = self.instance.amount
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.localdate()
        if user is not None:
            self.fields['category'].queryset = ExpenseCategory.objects.filter(
                Q(user__isnull=True) | Q(user=user), active=True
            )
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                Q(user__isnull=True) | Q(user=user), active=True
            )

    def clean(self):
        cleaned_data = super().clean()
        orig = cleaned_data.get('original_amount')
        currency = cleaned_data.get('currency', 'INR')
        rate = cleaned_data.get('exchange_rate') or Decimal('1.0000')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if currency == 'INR':
            rate = Decimal('1.0000')
            cleaned_data['exchange_rate'] = rate
        if orig is None or orig <= Decimal('0.00'):
            raise forms.ValidationError("Amount must be greater than 0.00.")
        if rate <= Decimal('0.0000'):
            raise forms.ValidationError("Exchange rate must be greater than 0.")
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be earlier than start date.")

        self.instance.amount = (orig * rate).quantize(Decimal('0.01'))
        return cleaned_data


class CurrencyRateForm(forms.ModelForm):
    class Meta:
        model = CurrencyRate
        fields = ['code', 'symbol', 'name', 'rate_to_base']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'e.g. JPY'}),
            'symbol': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '¥'}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Japanese Yen'}),
            'rate_to_base': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.0001', 'min': '0.0001'}),
        }