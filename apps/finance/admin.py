from django.contrib import admin
from .models import CurrencyRate, ExpenseCategory, PaymentMethod, Expense, Income, RecurringExpense


admin.site.register(ExpenseCategory)
admin.site.register(PaymentMethod)
admin.site.register(Expense)
admin.site.register(Income)
admin.site.register(RecurringExpense)
admin.site.register(CurrencyRate)