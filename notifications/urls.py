from django.urls import path
from .api_views import (
    NotificationConnectionActionAPIView, NotificationListAPIView,
    NotificationMarkReadAPIView, NotificationUnreadCountAPIView,
)
from .views import inbox

urlpatterns = [
    path('inbox/', inbox, name='notifications_inbox'),
    path('', NotificationListAPIView.as_view(), name='api_notifications'),
    path('unread-count/', NotificationUnreadCountAPIView.as_view(), name='api_notifications_unread'),
    path('<uuid:notification_id>/read/', NotificationMarkReadAPIView.as_view(), name='api_notification_read'),
    path('<uuid:notification_id>/<str:action>/', NotificationConnectionActionAPIView.as_view(), name='api_notification_action'),
]
