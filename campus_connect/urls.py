"""campus_connect URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from questionnaire.urls import questionnaire_hub, questionnaire_intro, questionnaire_questions
from matching.urls import explore_matches, matches_ready

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include('admin_dashboard.urls')),
    path('', include('core.urls')),
    path('auth/', include('accounts.urls')),
    path('profiles/', include('profiles.urls')),
    path('api/', include('profiles.api_urls')),
    path('api/questionnaire/', include('questionnaire.api_urls')),
    path('api/matches/', include('matching.api_urls')),
    path('api/connections/', include('connections.api_urls')),
    path('questionnaire/', include('questionnaire.urls')),
    path('matches/', include('matching.urls')),
    path('connections/', include('connections.urls')),
    path('communities/', include('communities.urls')),
    path('events/', include('events.urls')),
    path('chat/', include('chat.urls')),
    path('notifications/', include('notifications.urls')),
    path('questionnaire-intro/', questionnaire_intro, name='questionnaire_intro_legacy'),
    path('questionnaire-hub/', questionnaire_hub, name='questionnaire_hub_legacy'),
    path('question/', questionnaire_questions, name='question_legacy'),
    path('matches-ready/', matches_ready, name='matches_ready_legacy'),
    path('explore-matches/', explore_matches, name='explore_matches_legacy'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)