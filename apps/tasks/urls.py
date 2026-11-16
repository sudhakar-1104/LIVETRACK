from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list, name='list'),
    path('new/', views.task_create, name='create'),
    path('<int:pk>/edit/', views.task_edit, name='edit'),
    path('<int:pk>/toggle/', views.task_toggle_complete, name='toggle'),
    path('<int:pk>/delete/', views.task_delete, name='delete'),
    path('calendar/', views.calendar_view, name='calendar'),
]