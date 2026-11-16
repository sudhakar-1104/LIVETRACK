from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Sum
from django.utils import timezone
from apps.accounts.models import UserPreference
from apps.budgets.models import Budget
from apps.common.models import Notification
from apps.finance.models import Expense, RecurringExpense
from apps.tasks.models import Task


def sync_user_reminders(user, send_email=False):
    """Evaluate due tasks, overdue tasks, upcoming bills, and budget warnings."""
    pref, _ = UserPreference.objects.get_or_create(user=user)
    if not pref.enable_in_app_reminders and not (send_email and pref.enable_email_reminders):
        return []

    today = timezone.localdate()
    horizon = today + timedelta(days=pref.reminder_lead_days)
    created_alerts = []

    def _create_once(dedup_key, title, message, level='INFO', link=''):
        obj, created = Notification.objects.get_or_create(
            dedup_key=dedup_key,
            defaults={
                'user': user,
                'title': title,
                'message': message,
                'level': level,
                'link': link,
            }
        )
        if created:
            created_alerts.append(obj)

    # 1. Overdue Tasks
    overdue_tasks = Task.objects.filter(
        user=user,
        is_archived=False,
        status__in=['NOT_STARTED', 'IN_PROGRESS'],
        due_date__lt=today
    )
    for t in overdue_tasks:
        _create_once(
            dedup_key=f"task_overdue_{user.id}_{t.id}_{today}",
            title=f"Overdue Task: {t.title}",
            message=f"This task was due on {t.due_date.strftime('%d %b %Y')}.",
            level='DANGER',
            link='/tasks/'
        )

    # 2. Tasks Due Today or Within Lead Window
    upcoming_tasks = Task.objects.filter(
        user=user,
        is_archived=False,
        status__in=['NOT_STARTED', 'IN_PROGRESS'],
        due_date__range=(today, horizon)
    )
    for t in upcoming_tasks:
        when = "today" if t.due_date == today else f"on {t.due_date.strftime('%d %b %Y')}"
        _create_once(
            dedup_key=f"task_due_{user.id}_{t.id}_{t.due_date}",
            title=f"Task Due: {t.title}",
            message=f"Scheduled {when} ({t.get_priority_display()} priority).",
            level='WARNING' if t.due_date == today else 'INFO',
            link='/tasks/'
        )

    # 3. Upcoming Recurring Bills
    upcoming_bills = RecurringExpense.objects.filter(
        user=user,
        is_active=True,
        next_due_date__range=(today, horizon)
    )
    for bill in upcoming_bills:
        when = "today" if bill.next_due_date == today else f"on {bill.next_due_date.strftime('%d %b %Y')}"
        _create_once(
            dedup_key=f"bill_due_{user.id}_{bill.id}_{bill.next_due_date}",
            title=f"Upcoming Bill: {bill.description}",
            message=f"₹{bill.amount} due {when} via {bill.payment_method.name}.",
            level='WARNING',
            link='/finance/recurring/'
        )

    # 4. Monthly Budget Threshold Alerts
    month_expenses = Expense.objects.filter(
        user=user,
        is_archived=False,
        expense_date__year=today.year,
        expense_date__month=today.month
    )
    total_spend = month_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    cat_spend = {
        row['category_id']: row['total']
        for row in month_expenses.values('category_id').annotate(total=Sum('amount'))
    }

    for b in Budget.objects.filter(user=user, year=today.year, month=today.month).select_related('category'):
        actual = total_spend if b.category is None else cat_spend.get(b.category_id, Decimal('0.00'))
        if b.amount <= 0:
            continue
        util = round((actual / b.amount) * Decimal('100'), 1)
        label = b.category.name if b.category else "Overall Monthly Budget"
        if actual > b.amount:
            _create_once(
                dedup_key=f"budget_exceeded_{user.id}_{b.id}_{today.year}_{today.month}",
                title=f"Budget Exceeded: {label}",
                message=f"Spent ₹{actual} against your ₹{b.amount} budget ({util}%).",
                level='DANGER',
                link='/budgets/'
            )
        elif util >= pref.budget_warning_threshold:
            _create_once(
                dedup_key=f"budget_warn_{user.id}_{b.id}_{today.year}_{today.month}",
                title=f"Budget Warning: {label}",
                message=f"You have used {util}% (₹{actual} of ₹{b.amount}) of your monthly limit.",
                level='WARNING',
                link='/budgets/'
            )

    # 5. Optional Email Digest (printed to console in local dev via ConsoleEmailBackend)
    if send_email and pref.enable_email_reminders and user.email and created_alerts:
        lines = [f"- {a.title}: {a.message}" for a in created_alerts]
        send_mail(
            subject=f"LifeTrack Daily Reminders ({today.strftime('%d %b %Y')})",
            message="Here are your active LifeTrack reminders:\n\n" + "\n".join(lines),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@lifetrack.local'),
            recipient_list=[user.email],
            fail_silently=True,
        )

    return created_alerts