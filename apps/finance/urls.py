from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/new/', views.expense_create, name='expense_create'),
    path('expenses/<int:pk>/edit/', views.expense_edit, name='expense_edit'),
    path('expenses/<int:pk>/delete/', views.expense_delete, name='expense_delete'),

    path('income/', views.income_list, name='income_list'),
    path('income/new/', views.income_create, name='income_create'),
    path('income/<int:pk>/edit/', views.income_edit, name='income_edit'),
    path('income/<int:pk>/delete/', views.income_delete, name='income_delete'),

    path('categories/', views.manage_categories, name='categories'),
    path('categories/<str:item_type>/<int:pk>/toggle/', views.toggle_category_status, name='toggle_category'),

    path('recurring/', views.recurring_expense_list, name='recurring_list'),
    path('recurring/new/', views.recurring_expense_create, name='recurring_create'),
    path('recurring/<int:pk>/edit/', views.recurring_expense_edit, name='recurring_edit'),
    path('recurring/<int:pk>/toggle/', views.recurring_expense_toggle, name='recurring_toggle'),
    path('recurring/<int:pk>/run-now/', views.recurring_expense_run_now, name='recurring_run_now'),
    path('recurring/<int:pk>/delete/', views.recurring_expense_delete, name='recurring_delete'),
    path('currencies/', views.manage_currencies, name='currencies'),
]