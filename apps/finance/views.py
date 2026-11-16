from django.shortcuts import render

# Create your views here.
from decimal import Decimal
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import (
    ExpenseCategoryForm,
    ExpenseForm,
    IncomeForm,
    PaymentMethodForm,
    TaskCategoryForm,
    RecurringExpenseForm,
    CurrencyRateForm,
)
import json
from .models import CurrencyRate, Expense, ExpenseCategory, Income, PaymentMethod, RecurringExpense
from apps.tasks.models import TaskCategory


# --- EXPENSES ---

@login_required
def expense_list(request):
    expenses = Expense.objects.filter(user=request.user, is_archived=False).select_related('category', 'payment_method')

    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    payment_id = request.GET.get('payment_method', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if q:
        expenses = expenses.filter(Q(description__icontains=q) | Q(notes__icontains=q))
    if category_id:
        expenses = expenses.filter(category_id=category_id)
    if payment_id:
        expenses = expenses.filter(payment_method_id=payment_id)
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)

    total_amount = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    categories = ExpenseCategory.objects.filter(Q(user__isnull=True) | Q(user=request.user))
    payment_methods = PaymentMethod.objects.filter(Q(user__isnull=True) | Q(user=request.user))

    context = {
        'expenses': expenses,
        'total_amount': total_amount,
        'categories': categories,
        'payment_methods': payment_methods,
        'q': q,
        'category_id': category_id,
        'payment_id': payment_id,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'finance/expense_list.html', context)


@login_required
def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, f"Expense of ₹{expense.amount} recorded.")
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm(user=request.user)
    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'page_title': 'Record Expense',
        'cancel_url': 'finance:expense_list',
    })


@login_required
def expense_edit(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user, is_archived=False)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Expense updated.")
            return redirect('finance:expense_list')
    else:
        form = ExpenseForm(instance=expense, user=request.user)
    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'page_title': 'Edit Expense',
        'cancel_url': 'finance:expense_list',
    })


@login_required
@require_POST
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user, is_archived=False)
    expense.is_archived = True
    expense.save()
    messages.warning(request, "Expense archived.")
    return redirect('finance:expense_list')


# --- INCOME ---

@login_required
def income_list(request):
    incomes = Income.objects.filter(user=request.user, is_archived=False)

    q = request.GET.get('q', '').strip()
    source = request.GET.get('source', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if q:
        incomes = incomes.filter(Q(description__icontains=q) | Q(notes__icontains=q))
    if source:
        incomes = incomes.filter(source=source)
    if date_from:
        incomes = incomes.filter(income_date__gte=date_from)
    if date_to:
        incomes = incomes.filter(income_date__lte=date_to)

    total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    context = {
        'incomes': incomes,
        'total_income': total_income,
        'source_choices': Income.SOURCE_CHOICES,
        'q': q,
        'source': source,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'finance/income_list.html', context)


@login_required
def income_create(request):
    if request.method == 'POST':
        form = IncomeForm(request.POST)
        if form.is_valid():
            income = form.save(commit=False)
            income.user = request.user
            income.save()
            messages.success(request, f"Income of ₹{income.amount} recorded.")
            return redirect('finance:income_list')
    else:
        form = IncomeForm()
    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'page_title': 'Record Income',
        'cancel_url': 'finance:income_list',
    })


@login_required
def income_edit(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user, is_archived=False)
    if request.method == 'POST':
        form = IncomeForm(request.POST, instance=income)
        if form.is_valid():
            form.save()
            messages.success(request, "Income updated.")
            return redirect('finance:income_list')
    else:
        form = IncomeForm(instance=income)
    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'page_title': 'Edit Income',
        'cancel_url': 'finance:income_list',
    })


@login_required
@require_POST
def income_delete(request, pk):
    income = get_object_or_404(Income, pk=pk, user=request.user, is_archived=False)
    income.is_archived = True
    income.save()
    messages.warning(request, "Income record archived.")
    return redirect('finance:income_list')


# --- CATEGORIES & PAYMENT METHODS (M08) ---

@login_required
def manage_categories(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_expense_cat':
            form = ExpenseCategoryForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.user = request.user
                obj.save()
                messages.success(request, f"Added expense category '{obj.name}'.")
        elif action == 'add_payment_method':
            form = PaymentMethodForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.user = request.user
                obj.save()
                messages.success(request, f"Added payment method '{obj.name}'.")
        elif action == 'add_task_cat':
            form = TaskCategoryForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.user = request.user
                obj.save()
                messages.success(request, f"Added task category '{obj.name}'.")
        return redirect('finance:categories')

    context = {
        'expense_categories': ExpenseCategory.objects.filter(Q(user__isnull=True) | Q(user=request.user)),
        'payment_methods': PaymentMethod.objects.filter(Q(user__isnull=True) | Q(user=request.user)),
        'task_categories': TaskCategory.objects.filter(Q(user__isnull=True) | Q(user=request.user)),
        'exp_form': ExpenseCategoryForm(),
        'pay_form': PaymentMethodForm(),
        'task_form': TaskCategoryForm(),
    }
    return render(request, 'finance/manage_categories.html', context)


@login_required
@require_POST
def toggle_category_status(request, item_type, pk):
    if item_type == 'expense':
        obj = get_object_or_404(ExpenseCategory, pk=pk, user=request.user)
    elif item_type == 'payment':
        obj = get_object_or_404(PaymentMethod, pk=pk, user=request.user)
    else:
        obj = get_object_or_404(TaskCategory, pk=pk, user=request.user)
    obj.active = not obj.active
    obj.save()
    messages.info(request, f"Updated '{obj.name}' status.")
    return redirect('finance:categories')


# --- RECURRING EXPENSES & BILLS (M20.1) ---

@login_required
def recurring_expense_list(request):
    today = timezone.localdate()
    recurring_items = RecurringExpense.objects.filter(user=request.user).select_related('category', 'payment_method')

    monthly_committed = Decimal('0.00')
    for item in recurring_items.filter(is_active=True):
        if item.frequency == 'WEEKLY':
            monthly_committed += item.amount * Decimal('4.33')
        elif item.frequency == 'MONTHLY':
            monthly_committed += item.amount
        elif item.frequency == 'QUARTERLY':
            monthly_committed += item.amount / Decimal('3')
        elif item.frequency == 'YEARLY':
            monthly_committed += item.amount / Decimal('12')

    context = {
        'recurring_items': recurring_items,
        'monthly_committed': round(monthly_committed, 2),
        'today': today,
    }
    return render(request, 'finance/recurring_list.html', context)


@login_required
def recurring_expense_create(request):
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, user=request.user)
        if form.is_valid():
            rec = form.save(commit=False)
            rec.user = request.user
            rec.next_due_date = rec.start_date
            rec.save()
            generated = rec.generate_due_expenses()
            msg = f"Recurring bill '{rec.description}' scheduled."
            if generated:
                msg += f" ({generated} due expense entry logged automatically.)"
            messages.success(request, msg)
            return redirect('finance:recurring_list')
    else:
        form = RecurringExpenseForm(user=request.user)
    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'page_title': 'Add Recurring Expense / Bill',
        'cancel_url': 'finance:recurring_list',
    })


@login_required
def recurring_expense_edit(request, pk):
    rec = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = RecurringExpenseForm(request.POST, instance=rec, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Updated recurring bill '{rec.description}'.")
            return redirect('finance:recurring_list')
    else:
        form = RecurringExpenseForm(instance=rec, user=request.user)
    return render(request, 'finance/transaction_form.html', {
        'form': form,
        'page_title': 'Edit Recurring Expense / Bill',
        'cancel_url': 'finance:recurring_list',
    })


@login_required
@require_POST
def recurring_expense_toggle(request, pk):
    rec = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    rec.is_active = not rec.is_active
    rec.save()
    state = "resumed" if rec.is_active else "paused"
    messages.info(request, f"Recurring bill '{rec.description}' {state}.")
    return redirect('finance:recurring_list')


@login_required
@require_POST
def recurring_expense_run_now(request, pk):
    rec = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    due_dt = rec.next_due_date
    Expense.objects.create(
        user=request.user,
        amount=rec.amount,
        expense_date=timezone.localdate(),
        category=rec.category,
        payment_method=rec.payment_method,
        description=f"{rec.description} (Recurring)",
        notes=rec.notes,
    )
    rec.last_generated_date = due_dt
    next_dt = rec.calculate_next_date(due_dt)
    if rec.end_date and next_dt > rec.end_date:
        rec.is_active = False
    rec.next_due_date = next_dt
    rec.save()
    messages.success(request, f"Logged ₹{rec.amount} for '{rec.description}' and advanced next due date to {rec.next_due_date}.")
    return redirect('finance:recurring_list')


@login_required
@require_POST
def recurring_expense_delete(request, pk):
    rec = get_object_or_404(RecurringExpense, pk=pk, user=request.user)
    rec.delete()
    messages.warning(request, "Recurring bill schedule deleted (past expenses preserved).")
    return redirect('finance:recurring_list')


def _get_rates_json(user):
    qs = CurrencyRate.objects.filter(Q(user__isnull=True) | Q(user=user), is_active=True)
    rate_map = {c.code: str(c.rate_to_base) for c in qs}
    return json.dumps(rate_map)

@login_required
def manage_currencies(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_currency':
            form = CurrencyRateForm(request.POST)
            if form.is_valid():
                obj = form.save(commit=False)
                obj.user = request.user
                obj.code = obj.code.upper().strip()
                obj.save()
                messages.success(request, f"Added currency {obj.code} (1 {obj.code} = ₹{obj.rate_to_base}).")
                return redirect('finance:currencies')
        elif action == 'update_rate':
            pk = request.POST.get('pk')
            new_rate = request.POST.get('rate_to_base')
            curr = get_object_or_404(CurrencyRate, pk=pk)
            try:
                rate_dec = Decimal(new_rate)
                if rate_dec > 0:
                    if curr.user is None:
                        CurrencyRate.objects.update_or_create(
                            user=request.user, code=curr.code,
                            defaults={'symbol': curr.symbol, 'name': curr.name, 'rate_to_base': rate_dec}
                        )
                    else:
                        curr.rate_to_base = rate_dec
                        curr.save()
                    messages.success(request, f"Updated {curr.code} exchange rate to ₹{rate_dec}.")
            except Exception:
                messages.error(request, "Invalid exchange rate.")
            return redirect('finance:currencies')

    currencies = CurrencyRate.objects.filter(Q(user__isnull=True) | Q(user=request.user)).order_by('code', '-user_id')
    return render(request, 'finance/manage_currencies.html', {
        'currencies': currencies,
        'form': CurrencyRateForm(),
    })