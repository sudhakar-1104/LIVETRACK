from django import forms
from .models import CashInflow, CashSpend


class CashInflowForm(forms.ModelForm):
    class Meta:
        model = CashInflow
        fields = ['amount', 'source', 'entry_date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., ATM Withdrawal / Cash Handover'}),
            'entry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
        }


class CashSpendForm(forms.ModelForm):
    class Meta:
        model = CashSpend
        fields = ['amount', 'item', 'tag', 'spend_date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'item': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What did you spend cash on?'}),
            'tag': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Food, Travel, Misc...'}),
            'spend_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
        }