from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import path

from connections.models import Connection
from .models import Message

User = get_user_model()


def connected_users(user):
    return User.objects.filter(
        Q(sent_requests__recipient=user, sent_requests__status='ACCEPTED') |
        Q(received_requests__requester=user, received_requests__status='ACCEPTED')
    ).distinct()


@login_required
def chat_home(request):
    contacts = connected_users(request.user)
    messages = Message.objects.filter(
        Q(sender=request.user) | Q(recipient=request.user)
    ).select_related('sender', 'recipient')[:100]
    return render(request, 'chat/home.html', {
        'contacts': contacts,
        'messages': messages,
    })


@login_required
def unread_count(request):
    return JsonResponse({
        'unread_count': Message.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count(),
    })


@login_required
def conversation(request, user_id):
    other = User.objects.filter(id=user_id, is_active=True).first()
    if not other or not connected_users(request.user).filter(id=other.id).exists():
        raise Http404('You can only chat with an accepted connection.')
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if not content:
            return redirect('chat_conversation', user_id=other.id)
        Message.objects.create(sender=request.user, recipient=other, content=content)
        return redirect('chat_conversation', user_id=other.id)
    messages = Message.objects.filter(
        Q(sender=request.user, recipient=other) |
        Q(sender=other, recipient=request.user)
    ).select_related('sender', 'recipient').order_by('created_at')
    Message.objects.filter(sender=other, recipient=request.user, is_read=False).update(is_read=True)
    return render(request, 'chat/conversation.html', {
        'other': other,
        'messages': messages,
    })


@login_required
def send_message_api(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'detail': 'POST required.'}, status=405)
    other = User.objects.filter(id=user_id, is_active=True).first()
    if not other or not connected_users(request.user).filter(id=other.id).exists():
        return JsonResponse({'detail': 'You can only message accepted connections.'}, status=403)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'detail': 'Message cannot be empty.'}, status=400)
    message = Message.objects.create(sender=request.user, recipient=other, content=content)
    return JsonResponse({'id': str(message.id), 'content': message.content, 'created_at': message.created_at.isoformat()})


urlpatterns = [
    path('', chat_home, name='chat_home'),
    path('unread-count/', unread_count, name='chat_unread_count'),
    path('<uuid:user_id>/', conversation, name='chat_conversation'),
    path('<uuid:user_id>/send/', send_message_api, name='chat_send_message'),
]
