from django.urls import path

from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('users/', views.users, name='users'),
    path('users/<uuid:user_id>/', views.user_detail, name='user_detail'),
    path('users/<uuid:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<uuid:user_id>/toggle/', views.toggle_user, name='toggle_user'),
    path('roles/', views.roles, name='roles'),
    path('roles/new/', views.role_edit, name='role_new'),
    path('roles/<int:role_id>/edit/', views.role_edit, name='role_edit'),
    path('events/', views.events, name='events'),
    path('event-registrations/', views.event_registrations, name='event_registrations'),
    path('events/new/', views.event_edit, name='event_new'),
    path('events/<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('communities/', views.communities, name='communities'),
    path('community-joins/', views.community_joins, name='community_joins'),
    path('communities/new/', views.community_edit, name='community_new'),
    path('communities/<int:community_id>/edit/', views.community_edit, name='community_edit'),
    path('questionnaire/', views.questionnaire, name='questionnaire'),
    path('questionnaire/sections/new/', views.questionnaire_category_edit, name='category_new'),
    path('questionnaire/sections/<int:category_id>/edit/', views.questionnaire_category_edit, name='category_edit'),
    path('questionnaire/questions/new/', views.questionnaire_question_edit, name='question_new'),
    path('questionnaire/questions/<uuid:question_id>/edit/', views.questionnaire_question_edit, name='question_edit'),
    path('questionnaire/import-export/', views.questionnaire_import_export, name='questionnaire_import_export'),
    path('questionnaire/export.xlsx', views.export_questionnaire, name='export_questionnaire'),
    path('matches/', views.matches, name='matches'),
    path('notifications/', views.notifications, name='notifications'),
    path('reports/', views.reports, name='reports'),
    path('export/users.csv', views.export_users, name='export_users'),
]
