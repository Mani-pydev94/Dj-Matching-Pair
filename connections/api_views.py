from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from .models import Connection

User = get_user_model()

def get_connection(first, second):
    return Connection.objects.filter(
        Q(requester=first, recipient=second) |
        Q(requester=second, recipient=first)
    ).first()


def connection_data(connection, user):
    other = connection.recipient if connection.requester_id == user.id else connection.requester
    profile = getattr(other, 'profile', None)
    return {'id': str(connection.id), 'status': connection.status, 'user_id': str(other.id),
            'display_name': other.get_full_name() or other.email,
            'university': profile.university if profile else ''}


class ConnectionRequestAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        recipient = User.objects.select_related('profile').filter(id=request.data.get('user_id'), is_active=True).first()
        if not recipient or recipient == request.user:
            return Response({'detail': 'Invalid recipient.'}, status=400)
        if Connection.objects.filter(Q(requester=request.user, recipient=recipient, status='BLOCKED') |
                                     Q(requester=recipient, recipient=request.user, status='BLOCKED')).exists():
            return Response({'detail': 'This user is unavailable.'}, status=403)
        connection, created = Connection.objects.get_or_create(
            requester=request.user, recipient=recipient,
            defaults={'status': 'PENDING'})
        if not created and connection.status != 'DECLINED':
            return Response({'detail': 'A connection already exists.', 'connection': connection_data(connection, request.user)}, status=409)
        if not created:
            connection.status = 'PENDING'
            connection.save(update_fields=('status', 'updated_at'))
        Notification.objects.create(user=recipient, title='New connection request',
                                    message=f'{request.user.get_full_name() or request.user.email} wants to connect with you.',
                                    connection=connection)
        return Response(connection_data(connection, request.user), status=status.HTTP_201_CREATED)


class ConnectionListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        qs = Connection.objects.filter(Q(requester=request.user) | Q(recipient=request.user))
        return Response({'results': [connection_data(item, request.user) for item in qs]})


class ConnectionActionAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, connection_id, action):
        if action == 'cancel':
            connection = Connection.objects.filter(
                id=connection_id,
                status__in=('PENDING', 'ACCEPTED'),
            ).filter(
                Q(requester=request.user) | Q(recipient=request.user),
            ).first()
            if not connection:
                return Response({'detail': 'Request not found.'}, status=404)
            connection.status = 'DECLINED'
            connection.save(update_fields=('status', 'updated_at'))
            connection.notifications.filter(user=connection.recipient, is_read=False).update(is_read=True)
            other = connection.recipient if connection.requester_id == request.user.id else connection.requester
            Notification.objects.create(
                user=other,
                title='Connection cancelled',
                message=f'{request.user.get_full_name() or request.user.email} cancelled your connection.',
                connection=connection,
            )
            return Response(connection_data(connection, request.user))

        connection = Connection.objects.filter(id=connection_id, recipient=request.user, status='PENDING').first()
        if not connection:
            return Response({'detail': 'Request not found.'}, status=404)
        if action not in ('accept', 'reject'):
            return Response({'detail': 'Unsupported action.'}, status=400)
        connection.status = 'ACCEPTED' if action == 'accept' else 'DECLINED'
        connection.save(update_fields=('status', 'updated_at'))
        if action == 'accept':
            Notification.objects.create(user=connection.requester, title='Connection accepted',
                                        message=f'{request.user.get_full_name() or request.user.email} accepted your connection request.',
                                        connection=connection)
        Notification.objects.filter(
            user=request.user, connection=connection, is_read=False,
        ).update(is_read=True)
        return Response(connection_data(connection, request.user))
