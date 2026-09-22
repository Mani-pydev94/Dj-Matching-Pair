from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models import Q
from profiles.services import get_profile_completion

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'pages/landing.html')

@login_required
def home_view(request):
    profile_pct = get_profile_completion(request.user)
    questionnaire_done = hasattr(request.user, 'profile') and request.user.profile.questionnaire_completed
    top_matches = []
    if hasattr(request.user, 'profile'):
        try:
            from django.contrib.auth import get_user_model
            from matching.services import excluded_ids, is_discoverable, score_match
            User = get_user_model()
            candidates = User.objects.filter(
                is_active=True, profile__is_public=True,
                profile__questionnaire_completed=True,
            ).exclude(id__in=excluded_ids(request.user)).select_related('profile')
            ranked = []
            for candidate in candidates:
                breakdown = score_match(request.user, candidate)
                if is_discoverable(request.user, candidate, breakdown):
                    ranked.append((candidate, breakdown))
            from connections.models import Connection
            connected_ids = set(Connection.objects.filter(
                Q(requester=request.user, status='ACCEPTED') |
                Q(recipient=request.user, status='ACCEPTED'),
            ).values_list('requester_id', flat=True))
            connected_ids.update(Connection.objects.filter(
                Q(requester=request.user, status='ACCEPTED') |
                Q(recipient=request.user, status='ACCEPTED'),
            ).values_list('recipient_id', flat=True))
            top_matches = []
            for candidate, breakdown in sorted(
                ranked, key=lambda item: item[1]['overall_score'], reverse=True
            )[:5]:
                connected = candidate.id in connected_ids
                top_matches.append({
                    'id': candidate.id,
                    'first_name': candidate.first_name,
                    'last_name': candidate.last_name,
                    'compat': breakdown['overall_score'],
                    'can_view_full_profile': connected,
                    'is_private': not connected,
                    'photo_url': (
                        candidate.profile.photo.url
                        if connected and candidate.profile.photo else ''
                    ),
                    'university': candidate.profile.university if connected else '',
                    'interests': candidate.profile.interests if connected else '',
                })
        except Exception:
            top_matches = []
    communities = []
    try:
        from communities.models import Community
        communities = list(Community.objects.all()[:5])
    except Exception:
        pass
    events = []
    try:
        from events.models import Event
        events = list(Event.objects.all().order_by('start')[:5])
        from events.models import EventRegistration
        registered_event_ids = set(EventRegistration.objects.filter(
            user=request.user, event__in=events,
        ).values_list('event_id', flat=True))
    except Exception:
        pass
    return render(request, 'pages/home.html', {
        'profile_pct': profile_pct,
        'questionnaire_done': questionnaire_done,
        'student_name': request.user.get_full_name() or request.user.first_name or request.user.email,
        'top_matches': top_matches,
        'communities': communities,
        'events': events,
        'registered_event_ids': registered_event_ids if events else set(),
    })

urlpatterns = [
    path('', landing_view, name='landing'),
    path('home/', home_view, name='home'),
]
