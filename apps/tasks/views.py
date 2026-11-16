from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import TaskForm
from .models import Task, TaskCategory
import calendar
from datetime import date
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from apps.finance.models import Expense


@login_required
def task_list(request):
    tasks = Task.objects.filter(user=request.user, is_archived=False).select_related('category')

    # Filters
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    category_filter = request.GET.get('category', '')

    if q:
        tasks = tasks.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if status_filter == 'OVERDUE':
        tasks = [t for t in tasks if t.is_overdue]
    elif status_filter:
        tasks = tasks.filter(status=status_filter)
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    if category_filter:
        tasks = tasks.filter(category_id=category_filter)

    # Completion metrics (on all non-archived tasks for user, excluding Cancelled)
    all_user_tasks = Task.objects.filter(user=request.user, is_archived=False)
    eligible_tasks = all_user_tasks.exclude(status='CANCELLED')
    eligible_count = eligible_tasks.count()
    completed_count = eligible_tasks.filter(status='COMPLETED').count()
    completion_rate = round((completed_count / eligible_count) * 100, 1) if eligible_count > 0 else 0

    categories = TaskCategory.objects.filter(Q(user__isnull=True) | Q(user=request.user), active=True)

    context = {
        'tasks': tasks,
        'categories': categories,
        'q': q,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'eligible_count': eligible_count,
        'completed_count': completed_count,
        'completion_rate': completion_rate,
    }
    return render(request, 'tasks/task_list.html', context)


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST, user=request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            messages.success(request, f"Task '{task.title}' created.")
            return redirect('tasks:list')
    else:
        form = TaskForm(user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'page_title': 'Add New Task'})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_archived=False)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Task '{task.title}' updated.")
            return redirect('tasks:list')
    else:
        form = TaskForm(instance=task, user=request.user)
    return render(request, 'tasks/task_form.html', {'form': form, 'page_title': 'Edit Task', 'task': task})


@login_required
@require_POST
def task_toggle_complete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_archived=False)
    if task.status == 'COMPLETED':
        task.status = 'NOT_STARTED'
        messages.info(request, f"Reopened task '{task.title}'.")
    else:
        task.status = 'COMPLETED'
        messages.success(request, f"Completed task '{task.title}'!")
    task.save()
    next_url = request.POST.get('next') or 'tasks:list'
    return redirect(next_url)


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, user=request.user, is_archived=False)
    task.is_archived = True
    task.save()
    messages.warning(request, f"Task '{task.title}' archived.")
    return redirect('tasks:list')


@login_required
def calendar_view(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not (1 <= month <= 12):
            month = today.month
    except ValueError:
        year, month = today.year, today.month

    selected_day_str = request.GET.get('day', '')
    try:
        selected_date = date.fromisoformat(selected_day_str) if selected_day_str else today
    except ValueError:
        selected_date = today

    # Previous / Next month navigation
    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year

    # Fetch tasks and daily expense sums for the visible month
    month_tasks = Task.objects.filter(
        user=request.user,
        is_archived=False,
        due_date__year=year,
        due_date__month=month
    )
    tasks_by_day = {}
    for t in month_tasks:
        tasks_by_day.setdefault(t.due_date, []).append(t)

    month_expenses = Expense.objects.filter(
        user=request.user,
        is_archived=False,
        expense_date__year=year,
        expense_date__month=month
    ).values('expense_date').annotate(total=Sum('amount'))
    expense_by_day = {row['expense_date']: row['total'] for row in month_expenses}

    # Build calendar weeks (Monday start)
    cal = calendar.Calendar(firstweekday=0)
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        week_cells = []
        for day_obj in week:
            week_cells.append({
                'date': day_obj,
                'in_month': day_obj.month == month,
                'is_today': day_obj == today,
                'is_selected': day_obj == selected_date,
                'tasks': tasks_by_day.get(day_obj, []),
                'expense_total': expense_by_day.get(day_obj, Decimal('0.00')),
            })
        weeks.append(week_cells)

    # Selected day detailed records
    selected_tasks = Task.objects.filter(
        user=request.user,
        is_archived=False,
        due_date=selected_date
    ).select_related('category')
    selected_expenses = Expense.objects.filter(
        user=request.user,
        is_archived=False,
        expense_date=selected_date
    ).select_related('category', 'payment_method')

    context = {
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
        'weeks': weeks,
        'selected_date': selected_date,
        'selected_tasks': selected_tasks,
        'selected_expenses': selected_expenses,
    }
    return render(request, 'tasks/calendar.html', context)