"""campus_connect URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('auth/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('profiles/', include('profiles.urls')),
    path('questionnaire/', include('questionnaire.urls')),
    path('matches/', include('matching.urls')),
    path('connections/', include('connections.urls')),
    path('communities/', include('communities.urls')),
    path('events/', include('events.urls')),
    path('chat/', include('chat.urls')),
    path('notifications/', include('notifications.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)