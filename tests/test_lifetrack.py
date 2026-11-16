from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from apps.budgets.models import Budget
from apps.finance.models import Expense, ExpenseCategory, Income, PaymentMethod
from apps.tasks.models import Task


class LifeTrackAcceptanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='StrongPassword123!')
        self.other_user = User.objects.create_user(username='other', password='StrongPassword123!')
        self.exp_cat = ExpenseCategory.objects.create(name='Food & Dining')
        self.pay_method = PaymentMethod.objects.create(name='UPI')
        self.client.login(username='tester', password='StrongPassword123!')

    def test_auth_protection(self):
        self.client.logout()
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)

    def test_T01_T02_expense_creation_and_negative_rejection(self):
        # T01: Valid expense
        res = self.client.post(reverse('finance:expense_create'), {
            'amount': '250.00',
            'expense_date': date.today().isoformat(),
            'category': self.exp_cat.id,
            'payment_method': self.pay_method.id,
            'description': 'Lunch',
        })
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 1)

        # T02: Negative expense rejected
        res_neg = self.client.post(reverse('finance:expense_create'), {
            'amount': '-50.00',
            'expense_date': date.today().isoformat(),
            'category': self.exp_cat.id,
            'payment_method': self.pay_method.id,
            'description': 'Invalid',
        })
        self.assertEqual(res_neg.status_code, 200)
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 1)

    def test_T03_T04_year_and_month_boundaries(self):
        Expense.objects.create(
            user=self.user, amount=Decimal('500.00'), expense_date=date(2026, 12, 31),
            category=self.exp_cat, payment_method=self.pay_method, description='Year End'
        )
        Expense.objects.create(
            user=self.user, amount=Decimal('300.00'), expense_date=date(2027, 1, 1),
            category=self.exp_cat, payment_method=self.pay_method, description='New Year'
        )
        res_2026 = self.client.get(reverse('reports:index'), {'period': 'yearly', 'year': 2026})
        self.assertEqual(res_2026.context['total_expense'], Decimal('500.00'))

        res_2027 = self.client.get(reverse('reports:index'), {'period': 'yearly', 'year': 2027})
        self.assertEqual(res_2027.context['total_expense'], Decimal('300.00'))

    def test_T06_T07_budget_utilization_and_overspending(self):
        Budget.objects.create(user=self.user, year=2026, month=11, category=None, amount=Decimal('5000.00'))
        Expense.objects.create(
            user=self.user, amount=Decimal('4000.00'), expense_date=date(2026, 11, 10),
            category=self.exp_cat, payment_method=self.pay_method, description='Groceries'
        )
        # T06: 80% warning
        res = self.client.get(reverse('budgets:list'), {'year': 2026, 'month': 11})
        self.assertEqual(res.context['overall_row']['utilization'], Decimal('80.0'))
        self.assertEqual(res.context['overall_row']['remaining'], Decimal('1000.00'))
        self.assertEqual(res.context['overall_row']['status'], 'warning')

        # T07: 110% exceeded
        Expense.objects.create(
            user=self.user, amount=Decimal('1500.00'), expense_date=date(2026, 11, 15),
            category=self.exp_cat, payment_method=self.pay_method, description='Dining'
        )
        res_over = self.client.get(reverse('budgets:list'), {'year': 2026, 'month': 11})
        self.assertEqual(res_over.context['overall_row']['utilization'], Decimal('110.0'))
        self.assertEqual(res_over.context['overall_row']['remaining'], Decimal('-500.00'))
        self.assertEqual(res_over.context['overall_row']['status'], 'exceeded')

    def test_T08_task_completion_rate_and_recurrence(self):
        for i in range(3):
            Task.objects.create(user=self.user, title=f'Done {i}', status='COMPLETED')
        Task.objects.create(user=self.user, title='Pending 1', status='NOT_STARTED')
        Task.objects.create(user=self.user, title='Cancelled 1', status='CANCELLED')

        res = self.client.get(reverse('tasks:list'))
        # 3 completed out of 4 eligible (cancelled excluded) = 75.0%
        self.assertEqual(res.context['completion_rate'], 75.0)

    def test_T09_empty_period_zero_division_safety(self):
        res = self.client.get(reverse('reports:insights'), {'year': 2025, 'month': 2})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context['total_expense'], Decimal('0.00'))
        self.assertIsNone(res.context['mom_change'])

    def test_T11_csv_export(self):
        Expense.objects.create(
            user=self.user, amount=Decimal('120.00'), expense_date=date(2026, 11, 5),
            category=self.exp_cat, payment_method=self.pay_method, description='Coffee'
        )
        res = self.client.get(reverse('reports:export'), {'period': 'monthly', 'year': 2026, 'month': 11, 'format': 'csv'})
        self.assertEqual(res.status_code, 200)
        self.assertIn('Coffee', res.content.decode('utf-8'))

    def test_user_data_isolation(self):
        other_task = Task.objects.create(user=self.other_user, title='Secret Task')
        res = self.client.get(reverse('tasks:edit', args=[other_task.pk]))
        self.assertEqual(res.status_code, 404)