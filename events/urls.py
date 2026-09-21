from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, render
from django.urls import path
from django.views.decorators.http import require_POST

from .forms import EventRegistrationForm
from .models import Event, EventRegistration
from notifications.models import Notification


@login_required
def events_home(request):
    return render(request, 'events/home.html', {'events': Event.objects.all()})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'events/detail.html', {'event': event})


@login_required
@require_POST
def register_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if EventRegistration.objects.filter(event=event, user=request.user).exists():
        messages.info(request, f'You are already registered for {event.title}.')
        return redirect_home(request)
    form = EventRegistrationForm(request.POST)
    if form.is_valid():
        registration = form.save(commit=False)
        registration.event = event
        registration.user = request.user
        try:
            registration.save()
        except IntegrityError:
            messages.info(request, f'You are already registered for {event.title}.')
            return redirect_home(request)
        event.attendees.add(request.user)
        Notification.objects.create(
            user=request.user,
            title='Event registration successful',
            message=f'You are registered for {event.title}.',
        )
        messages.success(request, f'Registration successful for {event.title}.')
        return redirect_home(request)
    messages.error(request, 'Please enter a valid name, email, and phone number.')
    return redirect_home(request)


def redirect_home(request):
    from django.shortcuts import redirect
    return redirect('home')


urlpatterns = [
    path('', events_home, name='events_home'),
    path('<int:event_id>/', event_detail, name='event_detail'),
    path('<int:event_id>/register/', register_event, name='register_event'),
]
