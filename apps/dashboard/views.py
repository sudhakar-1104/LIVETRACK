from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from apps.accounts.models import UserPreference
from apps.budgets.models import Budget
from apps.finance.models import Expense, ExpenseCategory, Income, PaymentMethod, RecurringExpense
from apps.tasks.models import Task


@login_required
def index(request):
    today = timezone.localdate()
    # Auto-generate any due recurring expenses for this user
    auto_logged = 0
    for rec in RecurringExpense.objects.filter(user=request.user, is_active=True, next_due_date__lte=today):
        auto_logged += rec.generate_due_expenses(up_to_date=today)
    if auto_logged:
        messages.info(request, f"{auto_logged} due recurring bill(s) were automatically logged to Expenses.")
    preference, _ = UserPreference.objects.get_or_create(user=request.user)

    # Handle inline Quick-Add actions from Dashboard
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'quick_task':
            title = request.POST.get('title', '').strip()
            priority = request.POST.get('priority', 'MEDIUM')
            due_date = request.POST.get('due_date') or today
            if title:
                Task.objects.create(
                    user=request.user,
                    title=title,
                    priority=priority,
                    due_date=due_date,
                )
                messages.success(request, f"Quick task '{title}' added.")
            else:
                messages.error(request, "Task title cannot be empty.")
            return redirect('dashboard:index')

        elif action == 'quick_expense':
            amount_raw = request.POST.get('amount', '').strip()
            description = request.POST.get('description', '').strip()
            category_id = request.POST.get('category')
            payment_id = request.POST.get('payment_method')
            try:
                amount = Decimal(amount_raw)
                if amount <= Decimal('0.00'):
                    raise ValueError
                if not description or not category_id or not payment_id:
                    messages.error(request, "Please fill all expense fields.")
                else:
                    Expense.objects.create(
                        user=request.user,
                        amount=amount,
                        expense_date=today,
                        category_id=category_id,
                        payment_method_id=payment_id,
                        description=description,
                    )
                    messages.success(request, f"Expense of ₹{amount} logged.")
            except Exception:
                messages.error(request, "Please enter a valid positive amount.")
            return redirect('dashboard:index')

    # --- TASK METRICS ---
    active_tasks = Task.objects.filter(user=request.user, is_archived=False).select_related('category')
    open_tasks = active_tasks.filter(status__in=['NOT_STARTED', 'IN_PROGRESS'])

    todays_tasks = active_tasks.filter(due_date=today).order_by('status', '-priority')
    overdue_tasks = open_tasks.filter(due_date__lt=today)
    pending_count = open_tasks.count()
    overdue_count = overdue_tasks.count()

    eligible_tasks = active_tasks.exclude(status='CANCELLED')
    eligible_count = eligible_tasks.count()
    completed_count = eligible_tasks.filter(status='COMPLETED').count()
    completion_rate = round((completed_count / eligible_count) * 100, 1) if eligible_count > 0 else 0

    # --- FINANCE METRICS ---
    user_expenses = Expense.objects.filter(user=request.user, is_archived=False).select_related('category', 'payment_method')
    today_expense = user_expenses.filter(expense_date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    mtd_expense = user_expenses.filter(
        expense_date__year=today.year,
        expense_date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    mtd_income = Income.objects.filter(
        user=request.user,
        is_archived=False,
        income_date__year=today.year,
        income_date__month=today.month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    mtd_savings = mtd_income - mtd_expense
    recent_expenses = user_expenses[:5]

    # --- OVERALL BUDGET STATUS ---
    overall_budget = Budget.objects.filter(
        user=request.user,
        year=today.year,
        month=today.month,
        category__isnull=True
    ).first()

    budget_info = None
    if overall_budget:
        utilization = round((mtd_expense / overall_budget.amount) * Decimal('100'), 1)
        remaining = overall_budget.amount - mtd_expense
        if mtd_expense > overall_budget.amount:
            b_status = 'exceeded'
        elif utilization >= preference.budget_warning_threshold:
            b_status = 'warning'
        else:
            b_status = 'ok'
        budget_info = {
            'limit': overall_budget.amount,
            'remaining': remaining,
            'utilization': utilization,
            'bar_width': min(int(utilization), 100),
            'status': b_status,
        }

    # Dropdown options for quick-add expense
    expense_categories = ExpenseCategory.objects.filter(Q(user__isnull=True) | Q(user=request.user), active=True)
    payment_methods = PaymentMethod.objects.filter(Q(user__isnull=True) | Q(user=request.user), active=True)

    context = {
        'today': today,
        'todays_tasks': todays_tasks,
        'overdue_tasks': overdue_tasks[:5],
        'pending_count': pending_count,
        'overdue_count': overdue_count,
        'completed_count': completed_count,
        'eligible_count': eligible_count,
        'completion_rate': completion_rate,
        'today_expense': today_expense,
        'mtd_expense': mtd_expense,
        'mtd_income': mtd_income,
        'mtd_savings': mtd_savings,
        'recent_expenses': recent_expenses,
        'budget_info': budget_info,
        'expense_categories': expense_categories,
        'payment_methods': payment_methods,
    }
    return render(request, 'dashboard/index.html', context)