from django.urls import path
from . import views

app_name = 'cash_wallet'

urlpatterns = [
    path('', views.wallet_dashboard, name='index'),
    path('inflow/<int:pk>/delete/', views.delete_inflow, name='delete_inflow'),
    path('spend/<int:pk>/delete/', views.delete_spend, name='delete_spend'),
]