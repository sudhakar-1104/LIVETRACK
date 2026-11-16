from django import forms
from django.db.models import Q
from .models import Task, TaskCategory


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'category', 'priority', 'status',
            'start_date', 'due_date', 'recurrence', 'recurrence_end_date'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What needs to be done?'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional notes...'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'recurrence': forms.Select(attrs={'class': 'form-select'}),
            'recurrence_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['category'].queryset = TaskCategory.objects.filter(
                Q(user__isnull=True) | Q(user=user),
                active=True
            )
        self.fields['category'].empty_label = "No Category"

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        due_date = cleaned_data.get('due_date')
        recurrence = cleaned_data.get('recurrence')
        recurrence_end_date = cleaned_data.get('recurrence_end_date')

        if start_date and due_date and due_date < start_date:
            raise forms.ValidationError("Due date cannot be earlier than start date.")
        if recurrence != 'NONE' and not due_date:
            raise forms.ValidationError("Please set a Due Date for recurring tasks.")
        if recurrence_end_date and due_date and recurrence_end_date < due_date:
            raise forms.ValidationError("Recurrence end date cannot be earlier than due date.")
        return cleaned_data