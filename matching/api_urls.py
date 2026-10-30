from django.urls import path

from .api_views import (
    CompatibilityAPIView,
    CompatibilityInsightsAPIView,
    MatchesAPIView,
)

urlpatterns = [
    path('', MatchesAPIView.as_view(), name='api_matches'),
    path(
        '<uuid:user_id>/compatibility/insights/',
        CompatibilityInsightsAPIView.as_view(),
        name='api_compatibility_insights',
    ),
    path('<uuid:user_id>/compatibility/', CompatibilityAPIView.as_view(), name='api_compatibility'),
]
