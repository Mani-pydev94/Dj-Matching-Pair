from django.urls import path

from .api_views import (
    MyProfileAPIView,
    MyProfilePhotoAPIView,
    MyProfileStatsAPIView,
    MyProfileStrengthAPIView,
    PublicStudentProfileAPIView,
)

urlpatterns = [
    path('profile/me/', MyProfileAPIView.as_view(), name='api_profile_me'),
    path('profile/me/photo/', MyProfilePhotoAPIView.as_view(), name='api_profile_photo'),
    path('profile/me/stats/', MyProfileStatsAPIView.as_view(), name='api_profile_stats'),
    path('profile/me/strength/', MyProfileStrengthAPIView.as_view(), name='api_profile_strength'),
    path('students/<uuid:user_id>/profile/', PublicStudentProfileAPIView.as_view(), name='api_student_profile'),
]
