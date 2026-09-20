from django.urls import path

from .views import edit_profile, my_profile, profile_setup, student_profile

app_name = 'profiles'

urlpatterns = [
    path('setup/', profile_setup, name='profile_setup'),
    path('edit/', edit_profile, name='edit_profile'),
    path('<uuid:user_id>/', student_profile, name='student_profile'),
    path('', my_profile, name='my_profile'),
]
