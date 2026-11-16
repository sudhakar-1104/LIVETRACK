from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserPreference


class StyledLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = [
            'currency', 'currency_symbol', 'week_start', 'theme',
            'budget_warning_threshold', 'enable_in_app_reminders',
            'enable_email_reminders', 'reminder_lead_days'
        ]
        widgets = {
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control'}),
            'week_start': forms.Select(attrs={'class': 'form-select'}),
            'theme': forms.Select(attrs={'class': 'form-select'}),
            'budget_warning_threshold': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100}),
            'enable_in_app_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_email_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_lead_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 30}),
        }