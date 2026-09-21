from django.urls import path

from .api_views import CompatibilityAPIView, MatchesAPIView

urlpatterns = [
    path('', MatchesAPIView.as_view(), name='api_matches'),
    path('<uuid:user_id>/compatibility/', CompatibilityAPIView.as_view(), name='api_compatibility'),
]
