from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import RegisterForm, UserPreferenceForm
from .models import UserPreference
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to LifeTrack! Your account has been created.")
            return redirect('dashboard:index')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def settings_view(request):
    preference, _ = UserPreference.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferences updated successfully.")
            return redirect('accounts:settings')
    else:
        form = UserPreferenceForm(instance=preference)
    return render(request, 'accounts/settings.html', {'form': form})


@login_required
def download_backup(request):
    db_path = settings.DATABASES['default']['NAME']
    timestamp = timezone.localtime().strftime('%Y%m%d_%H%M%S')
    return FileResponse(
        open(db_path, 'rb'),
        as_attachment=True,
        filename=f"lifetrack_backup_{timestamp}.sqlite3"
    )