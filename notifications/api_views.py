from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification


def notification_data(item):
    return {
        'id': str(item.id), 'title': item.title, 'message': item.message,
        'is_read': item.is_read, 'created_at': item.created_at,
        'connection_id': str(item.connection_id) if item.connection_id else None,
    }


class NotificationListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        items = Notification.objects.filter(user=request.user)
        return Response({'results': [notification_data(item) for item in items],
                         'unread_count': items.filter(is_read=False).count()})


class NotificationUnreadCountAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({'unread_count': Notification.objects.filter(
            user=request.user, is_read=False).count()})


class NotificationMarkReadAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, notification_id):
        item = Notification.objects.filter(id=notification_id, user=request.user).first()
        if not item:
            return Response({'detail': 'Notification not found.'}, status=404)
        if not item.is_read:
            item.is_read = True
            item.save(update_fields=('is_read',))
        return Response(notification_data(item))


class NotificationConnectionActionAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, notification_id, action):
        item = Notification.objects.filter(
            id=notification_id, user=request.user, connection__recipient=request.user,
            connection__status='PENDING',
        ).select_related('connection').first()
        if not item or action not in ('accept', 'reject'):
            return Response({'detail': 'Request not found.'}, status=404)
        item.connection.status = 'ACCEPTED' if action == 'accept' else 'DECLINED'
        item.connection.save(update_fields=('status', 'updated_at'))
        item.is_read = True
        item.save(update_fields=('is_read',))
        if action == 'accept':
            Notification.objects.create(
                user=item.connection.requester,
                title='Connection accepted',
                message=f'{request.user.get_full_name() or request.user.email} accepted your connection request.',
                connection=item.connection,
            )
        return Response({'status': item.connection.status, 'notification': notification_data(item)})
