from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import FileResponse, JsonResponse, Http404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import path, reverse
from PIL import Image, UnidentifiedImageError

from connections.models import Connection
from .models import Message

User = get_user_model()
MAX_CHAT_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_CHAT_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def validate_chat_image(image):
    allowed_formats = {
        'image/jpeg': 'JPEG',
        'image/png': 'PNG',
        'image/webp': 'WEBP',
    }
    if image.content_type not in allowed_formats:
        return 'Only JPG, PNG, and WEBP images are allowed.'
    if image.size > MAX_CHAT_IMAGE_SIZE:
        return 'Images must be 5 MB or smaller.'
    try:
        uploaded_image = Image.open(image)
        if uploaded_image.format != allowed_formats[image.content_type]:
            return 'The selected file is not a valid image of the declared type.'
        uploaded_image.verify()
    except (UnidentifiedImageError, OSError):
        return 'Upload a valid image file.'
    image.seek(0)
    return None


def connected_users(user):
    return User.objects.filter(
        Q(sent_requests__recipient=user, sent_requests__status='ACCEPTED') |
        Q(received_requests__requester=user, received_requests__status='ACCEPTED')
    ).distinct()


@login_required
def chat_home(request):
    contacts = list(connected_users(request.user))
    contact_ids = [contact.id for contact in contacts]
    messages = Message.objects.filter(
        Q(sender=request.user, recipient_id__in=contact_ids) |
        Q(recipient=request.user, sender_id__in=contact_ids)
    ).select_related('sender').order_by('-created_at')
    latest_by_contact = {}
    unread_by_contact = {}
    for message in messages:
        contact_id = (
            message.recipient_id if message.sender_id == request.user.id
            else message.sender_id
        )
        latest_by_contact.setdefault(contact_id, message)
        if message.recipient_id == request.user.id and not message.is_read:
            unread_by_contact[contact_id] = unread_by_contact.get(contact_id, 0) + 1

    for contact in contacts:
        contact.latest_message = latest_by_contact.get(contact.id)
        contact.unread_count = unread_by_contact.get(contact.id, 0)
    contacts.sort(
        key=lambda contact: (
            contact.latest_message.created_at.timestamp()
            if contact.latest_message else 0
        ),
        reverse=True,
    )
    return render(request, 'chat/home.html', {
        'contacts': contacts,
        'unread_count': sum(unread_by_contact.values()),
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
        'chat_emojis': (
            '😀', '😃', '😄', '😁', '😆', '😊', '🙂', '😉',
            '😍', '🥰', '😎', '🤩', '🤗', '🤔', '😂', '🥳',
            '🙌', '👋', '👏', '💜', '❤️', '💯', '✨', '🎉',
            '📚', '☕', '🌟', '🚀',
        ),
    })


@login_required
def send_message_api(request, user_id):
    if request.method != 'POST':
        return JsonResponse({'detail': 'POST required.'}, status=405)
    other = User.objects.filter(id=user_id, is_active=True).first()
    if not other or not connected_users(request.user).filter(id=other.id).exists():
        return JsonResponse({'detail': 'You can only message accepted connections.'}, status=403)
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    if len(content) > 2000:
        return JsonResponse({'detail': 'Messages must be 2,000 characters or fewer.'}, status=400)
    if not content and not image:
        return JsonResponse({'detail': 'Add a message or photo before sending.'}, status=400)
    if image:
        image_error = validate_chat_image(image)
        if image_error:
            return JsonResponse({'detail': image_error}, status=400)
    message = Message.objects.create(
        sender=request.user,
        recipient=other,
        content=content,
        image=image,
    )
    return JsonResponse({
        'id': str(message.id),
        'content': message.content,
        'image_url': (
            request.build_absolute_uri(reverse('chat_message_image', args=[message.id]))
            if message.image else None
        ),
        'created_at': message.created_at.isoformat(),
    })


@login_required
def chat_message_image(request, message_id):
    message = Message.objects.filter(id=message_id).select_related('sender', 'recipient').first()
    other_id = None
    if message and request.user.id in (message.sender_id, message.recipient_id):
        other_id = (
            message.recipient_id if message.sender_id == request.user.id
            else message.sender_id
        )
    if (
        not message or not message.image or
        other_id is None or
        not connected_users(request.user).filter(id=other_id).exists()
    ):
        raise Http404('Chat image not found.')
    try:
        with Image.open(message.image) as image:
            image_format = image.format
    except (UnidentifiedImageError, OSError):
        raise Http404('Chat image not found.')
    content_type = {
        'JPEG': 'image/jpeg',
        'PNG': 'image/png',
        'WEBP': 'image/webp',
    }.get(image_format)
    if content_type not in ALLOWED_CHAT_IMAGE_TYPES:
        raise Http404('Chat image not found.')
    image_file = message.image.open('rb')
    return FileResponse(image_file, content_type=content_type)


@login_required
def conversation_messages_api(request, user_id):
    if request.method != 'GET':
        return JsonResponse({'detail': 'GET required.'}, status=405)
    other = User.objects.filter(id=user_id, is_active=True).first()
    if not other or not connected_users(request.user).filter(id=other.id).exists():
        return JsonResponse({'detail': 'You can only read messages with an accepted connection.'}, status=403)

    conversation_messages = Message.objects.filter(
        Q(sender=request.user, recipient=other) |
        Q(sender=other, recipient=request.user)
    )
    after = request.GET.get('after')
    if after:
        try:
            cursor_id = UUID(after)
        except ValueError:
            return JsonResponse({'detail': 'Invalid message cursor.'}, status=400)
        cursor = conversation_messages.filter(id=cursor_id).first()
        if cursor is None:
            return JsonResponse({'detail': 'Message cursor not found.'}, status=400)
        conversation_messages = conversation_messages.filter(
            Q(created_at__gt=cursor.created_at) |
            Q(created_at=cursor.created_at, id__gt=cursor.id)
        )

    messages = list(conversation_messages.select_related('sender').order_by('created_at', 'id'))
    incoming_ids = [message.id for message in messages if message.recipient_id == request.user.id]
    if incoming_ids:
        Message.objects.filter(id__in=incoming_ids, is_read=False).update(is_read=True)

    return JsonResponse({
        'messages': [{
            'id': str(message.id),
            'content': message.content,
            'created_at': message.created_at.isoformat(),
            'is_mine': message.sender_id == request.user.id,
            'image_url': (
                request.build_absolute_uri(reverse('chat_message_image', args=[message.id]))
                if message.image else None
            ),
        } for message in messages],
    })


urlpatterns = [
    path('', chat_home, name='chat_home'),
    path('unread-count/', unread_count, name='chat_unread_count'),
    path('image/<uuid:message_id>/', chat_message_image, name='chat_message_image'),
    path('<uuid:user_id>/messages/', conversation_messages_api, name='chat_messages'),
    path('<uuid:user_id>/', conversation, name='chat_conversation'),
    path('<uuid:user_id>/send/', send_message_api, name='chat_send_message'),
]
