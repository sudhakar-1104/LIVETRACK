import calendar
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel


def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return source_date.replace(year=year, month=month, day=day)


class TaskCategory(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='task_categories'
    )
    name = models.CharField(max_length=100)
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Task Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Task(TimeStampedModel):
    PRIORITY_CHOICES = [
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
    ]
    STATUS_CHOICES = [
        ('NOT_STARTED', 'Not Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    RECURRENCE_CHOICES = [
        ('NONE', 'Does not repeat'),
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('MONTHLY', 'Monthly'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks'
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='NOT_STARTED')
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default='NONE')
    recurrence_end_date = models.DateField(null=True, blank=True)
    next_occurrence_created = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['due_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'due_date']),
        ]

    @property
    def is_overdue(self):
        if self.due_date and self.status in ('NOT_STARTED', 'IN_PROGRESS'):
            return self.due_date < timezone.localdate()
        return False

    def _get_next_due_date(self):
        base_date = self.due_date or timezone.localdate()
        if self.recurrence == 'DAILY':
            return base_date + timedelta(days=1)
        elif self.recurrence == 'WEEKLY':
            return base_date + timedelta(weeks=1)
        elif self.recurrence == 'MONTHLY':
            return add_months(base_date, 1)
        return None

    def save(self, *args, **kwargs):
        just_completed = False
        if self.status == 'COMPLETED':
            if not self.completed_at:
                self.completed_at = timezone.now()
                just_completed = True
        else:
            self.completed_at = None

        should_spawn_next = (
            just_completed
            and self.recurrence != 'NONE'
            and not self.next_occurrence_created
        )

        if should_spawn_next:
            next_due = self._get_next_due_date()
            if next_due and (not self.recurrence_end_date or next_due <= self.recurrence_end_date):
                self.next_occurrence_created = True
                super().save(*args, **kwargs)
                Task.objects.create(
                    user=self.user,
                    title=self.title,
                    description=self.description,
                    category=self.category,
                    priority=self.priority,
                    status='NOT_STARTED',
                    due_date=next_due,
                    recurrence=self.recurrence,
                    recurrence_end_date=self.recurrence_end_date,
                )
                return

        super().save(*args, **kwargs)

    def __str__(self):
        return self.title