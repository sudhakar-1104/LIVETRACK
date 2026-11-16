from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_view, name='index'),
    path('insights/', views.insights_view, name='insights'),
    path('export/', views.export_report, name='export'),
    path('simulator/', views.simulator_view, name='simulator'),
]