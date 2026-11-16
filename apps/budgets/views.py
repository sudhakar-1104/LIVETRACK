from django.shortcuts import render

# Create your views here.
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import BudgetForm
from .models import Budget
from apps.accounts.models import UserPreference
from apps.finance.models import Expense, Income


def _calculate_budget_row(budget, actual_spend, warning_threshold):
    utilization = round((actual_spend / budget.amount) * Decimal('100'), 1) if budget.amount > 0 else Decimal('0.0')
    remaining = budget.amount - actual_spend

    if actual_spend > budget.amount:
        status = 'exceeded'
    elif utilization >= warning_threshold:
        status = 'warning'
    else:
        status = 'ok'

    return {
        'budget': budget,
        'actual': actual_spend,
        'remaining': remaining,
        'utilization': utilization,
        'bar_width': min(int(utilization), 100),
        'status': status,
    }


@login_required
def budget_list(request):
    today = timezone.localdate()
    try:
        selected_year = int(request.GET.get('year', today.year))
        selected_month = int(request.GET.get('month', today.month))
        if not (1 <= selected_month <= 12):
            selected_month = today.month
    except ValueError:
        selected_year = today.year
        selected_month = today.month

    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    warning_threshold = preference.budget_warning_threshold

    # Handle inline add/update budget
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            year = form.cleaned_data['year']
            month = int(form.cleaned_data['month'])
            category = form.cleaned_data['category']
            amount = form.cleaned_data['amount']

            budget_obj, created = Budget.objects.update_or_create(
                user=request.user,
                year=year,
                month=month,
                category=category,
                defaults={'amount': amount}
            )
            label = category.name if category else "Overall Monthly Budget"
            action_word = "set" if created else "updated"
            messages.success(request, f"{label} for {month:02d}/{year} {action_word} to ₹{amount}.")
            return redirect(f"{request.path}?year={year}&month={month}")
    else:
        form = BudgetForm(
            initial={'year': selected_year, 'month': selected_month},
            user=request.user
        )

    # Fetch month expenses and income
    month_expenses = Expense.objects.filter(
        user=request.user,
        is_archived=False,
        expense_date__year=selected_year,
        expense_date__month=selected_month
    )
    total_expense = month_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    total_income = Income.objects.filter(
        user=request.user,
        is_archived=False,
        income_date__year=selected_year,
        income_date__month=selected_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    savings_estimate = total_income - total_expense

    # Category spend lookup map
    cat_spend_qs = month_expenses.values('category_id').annotate(total=Sum('amount'))
    cat_spend_map = {row['category_id']: row['total'] for row in cat_spend_qs}

    # Budgets for selected month
    budgets_qs = Budget.objects.filter(
        user=request.user,
        year=selected_year,
        month=selected_month
    ).select_related('category')

    overall_row = None
    category_rows = []
    for b in budgets_qs:
        if b.category is None:
            overall_row = _calculate_budget_row(b, total_expense, warning_threshold)
        else:
            actual = cat_spend_map.get(b.category_id, Decimal('0.00'))
            category_rows.append(_calculate_budget_row(b, actual, warning_threshold))

    context = {
        'form': form,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_choices': BudgetForm.MONTH_CHOICES,
        'overall_row': overall_row,
        'category_rows': category_rows,
        'total_expense': total_expense,
        'total_income': total_income,
        'savings_estimate': savings_estimate,
        'warning_threshold': warning_threshold,
    }
    return render(request, 'budgets/budget_list.html', context)


@login_required
@require_POST
def budget_delete(request, pk):
    budget = get_object_or_404(Budget, pk=pk, user=request.user)
    year, month = budget.year, budget.month
    budget.delete()
    messages.warning(request, "Budget removed.")
    return redirect(f"/budgets/?year={year}&month={month}")