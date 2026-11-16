import calendar
import csv
import json
from datetime import date, timedelta
from decimal import Decimal
import openpyxl
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from apps.finance.models import Expense, Income
from apps.tasks.models import Task


def _resolve_date_range(request):
    today = timezone.localdate()
    period = request.GET.get('period', 'monthly')

    if period == 'daily':
        ref_str = request.GET.get('date', '')
        try:
            ref_date = date.fromisoformat(ref_str) if ref_str else today
        except ValueError:
            ref_date = today
        return period, ref_date, ref_date, ref_date.strftime('%d %b %Y')

    elif period == 'weekly':
        ref_str = request.GET.get('date', '')
        try:
            ref_date = date.fromisoformat(ref_str) if ref_str else today
        except ValueError:
            ref_date = today
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=6)
        label = f"{start_date.strftime('%d %b')} – {end_date.strftime('%d %b %Y')}"
        return period, start_date, end_date, label

    elif period == 'yearly':
        try:
            year = int(request.GET.get('year', today.year))
        except ValueError:
            year = today.year
        return period, date(year, 1, 1), date(year, 12, 31), f"Year {year}"

    elif period == 'custom':
        try:
            start_date = date.fromisoformat(request.GET.get('start', ''))
            end_date = date.fromisoformat(request.GET.get('end', ''))
            if end_date < start_date:
                start_date, end_date = end_date, start_date
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
        label = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"
        return period, start_date, end_date, label

    else:  # default: monthly
        period = 'monthly'
        try:
            year = int(request.GET.get('year', today.year))
            month = int(request.GET.get('month', today.month))
            if not (1 <= month <= 12):
                month = today.month
        except ValueError:
            year, month = today.year, today.month
        last_day = calendar.monthrange(year, month)[1]
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        label = f"{calendar.month_name[month]} {year}"
        return period, start_date, end_date, label


def _build_report_data(user, start_date, end_date):
    expenses = Expense.objects.filter(
        user=user,
        is_archived=False,
        expense_date__range=(start_date, end_date)
    ).select_related('category', 'payment_method')

    incomes = Income.objects.filter(
        user=user,
        is_archived=False,
        income_date__range=(start_date, end_date)
    )

    tasks = Task.objects.filter(
        user=user,
        is_archived=False,
        due_date__range=(start_date, end_date)
    )

    total_expense = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_income = incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    net_cash_flow = total_income - total_expense

    num_days = (end_date - start_date).days + 1
    avg_daily_expense = round(total_expense / Decimal(num_days), 2) if num_days > 0 else Decimal('0.00')

    # Category breakdown
    category_breakdown = list(
        expenses.values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    for row in category_breakdown:
        row['share'] = round((row['total'] / total_expense) * Decimal('100'), 1) if total_expense > 0 else Decimal('0.0')

    top_category = category_breakdown[0] if category_breakdown else None

    # Highest-spend day
    daily_totals = list(
        expenses.values('expense_date')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    highest_spend_day = daily_totals[0] if daily_totals else None

    # Task completion metrics
    eligible_tasks = tasks.exclude(status='CANCELLED')
    eligible_count = eligible_tasks.count()
    completed_count = eligible_tasks.filter(status='COMPLETED').count()
    completion_rate = round((completed_count / eligible_count) * 100, 1) if eligible_count > 0 else 0

    return {
        'expenses': expenses,
        'incomes': incomes,
        'tasks': tasks,
        'total_expense': total_expense,
        'total_income': total_income,
        'net_cash_flow': net_cash_flow,
        'num_days': num_days,
        'avg_daily_expense': avg_daily_expense,
        'category_breakdown': category_breakdown,
        'top_category': top_category,
        'highest_spend_day': highest_spend_day,
        'eligible_count': eligible_count,
        'completed_count': completed_count,
        'completion_rate': completion_rate,
    }


@login_required
def report_view(request):
    today = timezone.localdate()
    period, start_date, end_date, period_label = _resolve_date_range(request)
    data = _build_report_data(request.user, start_date, end_date)

    context = {
        **data,
        'period': period,
        'start_date': start_date,
        'end_date': end_date,
        'period_label': period_label,
        'selected_year': start_date.year,
        'selected_month': start_date.month,
        'month_choices': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'today': today,
    }
    return render(request, 'reports/report.html', context)


@login_required
def insights_view(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not (1 <= month <= 12):
            month = today.month
    except ValueError:
        year, month = today.year, today.month

    last_day = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)
    data = _build_report_data(request.user, start_date, end_date)

    # 1. Savings Rate %
    if data['total_income'] > 0:
        savings_rate = round((data['net_cash_flow'] / data['total_income']) * Decimal('100'), 1)
    else:
        savings_rate = None

    # 2. Active-Spend-Day Average & Month-End Spend Forecast
    active_spend_days = data['expenses'].values('expense_date').distinct().count()
    active_day_avg = round(data['total_expense'] / Decimal(active_spend_days), 2) if active_spend_days > 0 else Decimal('0.00')

    if year == today.year and month == today.month and today.day > 0:
        projected_month_spend = round((data['total_expense'] / Decimal(today.day)) * Decimal(last_day), 2)
    else:
        projected_month_spend = data['total_expense']

    # 3. Month-on-Month Comparison
    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year
    prev_total = Expense.objects.filter(
        user=request.user,
        is_archived=False,
        expense_date__year=prev_year,
        expense_date__month=prev_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    if prev_total > 0:
        mom_change = round(((data['total_expense'] - prev_total) / prev_total) * Decimal('100'), 1)
    else:
        mom_change = None  # Zero baseline handled safely (T09)

    # 4. Payment Method Breakdown
    payment_breakdown = list(
        data['expenses'].values('payment_method__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )
    for row in payment_breakdown:
        row['share'] = round((row['total'] / data['total_expense']) * Decimal('100'), 1) if data['total_expense'] > 0 else Decimal('0.0')

    # 5. Day-of-Week Spending Pattern (Mon=0 .. Sun=6)
    weekday_totals = [Decimal('0.00')] * 7
    for exp in data['expenses']:
        weekday_totals[exp.expense_date.weekday()] += exp.amount
    weekday_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    weekday_values = [float(val) for val in weekday_totals]
    peak_weekday_idx = weekday_totals.index(max(weekday_totals)) if data['total_expense'] > 0 else None
    peak_weekday = weekday_labels[peak_weekday_idx] if peak_weekday_idx is not None else None

    # 6. 12-Month Rolling Trend (Income, Expense, Net Savings, Task Completion %)
    trend_labels = []
    trend_expenses = []
    trend_incomes = []
    trend_savings = []
    trend_task_rates = []

    cur_y, cur_m = year, month
    months_seq = []
    for _ in range(12):
        months_seq.append((cur_y, cur_m))
        cur_m -= 1
        if cur_m == 0:
            cur_m = 12
            cur_y -= 1
    months_seq.reverse()

    for y_i, m_i in months_seq:
        trend_labels.append(f"{calendar.month_abbr[m_i]} {str(y_i)[2:]}")
        e_sum = Expense.objects.filter(
            user=request.user, is_archived=False,
            expense_date__year=y_i, expense_date__month=m_i
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        i_sum = Income.objects.filter(
            user=request.user, is_archived=False,
            income_date__year=y_i, income_date__month=m_i
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        m_tasks = Task.objects.filter(
            user=request.user, is_archived=False,
            due_date__year=y_i, due_date__month=m_i
        ).exclude(status='CANCELLED')
        elig = m_tasks.count()
        comp = m_tasks.filter(status='COMPLETED').count()
        t_rate = round((comp / elig) * 100, 1) if elig > 0 else 0

        trend_expenses.append(float(e_sum))
        trend_incomes.append(float(i_sum))
        trend_savings.append(float(i_sum - e_sum))
        trend_task_rates.append(t_rate)

    cat_labels = [row['category__name'] for row in data['category_breakdown']]
    cat_values = [float(row['total']) for row in data['category_breakdown']]

    context = {
        **data,
        'selected_year': year,
        'selected_month': month,
        'month_name': calendar.month_name[month],
        'month_choices': [(i, calendar.month_name[i]) for i in range(1, 13)],
        'savings_rate': savings_rate,
        'active_spend_days': active_spend_days,
        'active_day_avg': active_day_avg,
        'projected_month_spend': projected_month_spend,
        'prev_total': prev_total,
        'mom_change': mom_change,
        'payment_breakdown': payment_breakdown,
        'peak_weekday': peak_weekday,
        'cat_labels_json': json.dumps(cat_labels),
        'cat_values_json': json.dumps(cat_values),
        'weekday_labels_json': json.dumps(weekday_labels),
        'weekday_values_json': json.dumps(weekday_values),
        'trend_labels_json': json.dumps(trend_labels),
        'trend_expenses_json': json.dumps(trend_expenses),
        'trend_incomes_json': json.dumps(trend_incomes),
        'trend_savings_json': json.dumps(trend_savings),
        'trend_task_rates_json': json.dumps(trend_task_rates),
    }
    return render(request, 'reports/insights.html', context)


@login_required
def export_report(request):
    fmt = request.GET.get('format', 'csv').lower()
    period, start_date, end_date, period_label = _resolve_date_range(request)
    data = _build_report_data(request.user, start_date, end_date)
    filename_base = f"lifetrack_report_{start_date}_{end_date}"

    if fmt == 'xlsx':
        wb = openpyxl.Workbook()
        ws_summary = wb.active
        ws_summary.title = "Summary"
        ws_summary.append(["LifeTrack Report", period_label])
        ws_summary.append(["Start Date", str(start_date)])
        ws_summary.append(["End Date", str(end_date)])
        ws_summary.append([])
        ws_summary.append(["Metric", "Value"])
        ws_summary.append(["Total Income (INR)", float(data['total_income'])])
        ws_summary.append(["Total Expenses (INR)", float(data['total_expense'])])
        ws_summary.append(["Net Cash-Flow Estimate (INR)", float(data['net_cash_flow'])])
        ws_summary.append(["Tasks Completed", f"{data['completed_count']} / {data['eligible_count']} ({data['completion_rate']}%)"])

        ws_exp = wb.create_sheet("Expenses")
        ws_exp.append(["Date", "Description", "Category", "Payment Method", "Amount (INR)", "Notes"])
        for e in data['expenses']:
            ws_exp.append([str(e.expense_date), e.description, e.category.name, e.payment_method.name, float(e.amount), e.notes])

        ws_inc = wb.create_sheet("Income")
        ws_inc.append(["Date", "Description", "Source", "Amount (INR)", "Notes"])
        for i in data['incomes']:
            ws_inc.append([str(i.income_date), i.description, i.get_source_display(), float(i.amount), i.notes])

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{filename_base}.xlsx"'
        wb.save(response)
        return response

    # Default: CSV export
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename_base}.csv"'
    writer = csv.writer(response)
    writer.writerow(["LifeTrack Report", period_label, f"{start_date} to {end_date}"])
    writer.writerow(["Total Income", data['total_income'], "Total Expenses", data['total_expense'], "Net Cash-Flow", data['net_cash_flow']])
    writer.writerow([])
    writer.writerow(["Type", "Date", "Description", "Category / Source", "Payment Method", "Amount (INR)", "Notes"])

    for e in data['expenses']:
        writer.writerow(["Expense", e.expense_date, e.description, e.category.name, e.payment_method.name, e.amount, e.notes])
    for i in data['incomes']:
        writer.writerow(["Income", i.income_date, i.description, i.get_source_display(), "-", i.amount, i.notes])

    return response


@login_required
def simulator_view(request):
    today = timezone.localdate()

    # Use up to the last 3 months of actual data (or current month if new) for realistic baselines
    three_months_ago = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
    recent_expenses = Expense.objects.filter(
        user=request.user,
        is_archived=False,
        expense_date__gte=three_months_ago
    )
    recent_incomes = Income.objects.filter(
        user=request.user,
        is_archived=False,
        income_date__gte=three_months_ago
    )

    distinct_exp_months = recent_expenses.dates('expense_date', 'month').count() or 1
    distinct_inc_months = recent_incomes.dates('income_date', 'month').count() or 1

    total_recent_exp = recent_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_recent_inc = recent_incomes.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    avg_monthly_income = round(total_recent_inc / Decimal(distinct_inc_months), 2)
    avg_monthly_expense = round(total_recent_exp / Decimal(distinct_exp_months), 2)

    # Category-wise monthly averages for interactive sliders
    raw_categories = list(
        recent_expenses.values('category__id', 'category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    category_baselines = []
    for row in raw_categories:
        monthly_avg = round(row['total'] / Decimal(distinct_exp_months), 2)
        category_baselines.append({
            'id': row['category__id'],
            'name': row['category__name'],
            'baseline': float(monthly_avg),
        })

    # Fallback sample categories if the user has zero logged expenses yet
    if not category_baselines:
        category_baselines = [
            {'id': 1, 'name': 'Food & Dining', 'baseline': 8000.0},
            {'id': 2, 'name': 'Shopping & Lifestyle', 'baseline': 6000.0},
            {'id': 3, 'name': 'Transport & Fuel', 'baseline': 4000.0},
            {'id': 4, 'name': 'Subscriptions & Bills', 'baseline': 3000.0},
        ]
        if avg_monthly_income == 0:
            avg_monthly_income = Decimal('50000.00')

    context = {
        'baseline_income': float(avg_monthly_income),
        'baseline_expense': float(sum(c['baseline'] for c in category_baselines)),
        'category_baselines': category_baselines,
        'category_baselines_json': json.dumps(category_baselines),
        'months_sampled': distinct_exp_months,
    }
    return render(request, 'reports/simulator.html', context)