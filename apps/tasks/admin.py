from django.contrib import admin
from .models import TaskCategory, Task

admin.site.register(TaskCategory)
admin.site.register(Task)