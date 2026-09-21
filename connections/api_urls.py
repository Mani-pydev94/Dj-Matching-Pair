from django.urls import path
from .api_views import ConnectionActionAPIView, ConnectionListAPIView, ConnectionRequestAPIView

urlpatterns = [
    path('', ConnectionListAPIView.as_view(), name='api_connections'),
    path('request/', ConnectionRequestAPIView.as_view(), name='api_connection_request'),
    path('requests/', ConnectionRequestAPIView.as_view(), name='api_connection_requests'),
    path('<uuid:connection_id>/<str:action>/', ConnectionActionAPIView.as_view(), name='api_connection_action'),
]
