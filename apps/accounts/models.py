from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.common.models import TimeStampedModel


class UserPreference(TimeStampedModel):
    WEEK_START_CHOICES = [
        ('MON', 'Monday'),
        ('SUN', 'Sunday'),
    ]
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preference'
    )
    currency = models.CharField(max_length=10, default='INR')
    currency_symbol = models.CharField(max_length=5, default='₹')
    week_start = models.CharField(max_length=3, choices=WEEK_START_CHOICES, default='MON')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    budget_warning_threshold = models.PositiveSmallIntegerField(default=80)

    enable_in_app_reminders = models.BooleanField(default=True)
    enable_email_reminders = models.BooleanField(default=False)
    reminder_lead_days = models.PositiveSmallIntegerField(
        default=1,
        help_text="Notify this many days before tasks or recurring bills are due."
    )




    def __str__(self):
        return f"{self.user.username} Preferences"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_user_preference(sender, instance, created, **kwargs):
    if created:
        UserPreference.objects.create(user=instance)