from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Notification


@login_required
def inbox(request):
    notifications = Notification.objects.filter(user=request.user).select_related('connection')
    return render(request, 'notifications/inbox.html', {
        'notifications': notifications,
        'unread_count': notifications.filter(is_read=False).count(),
    })
