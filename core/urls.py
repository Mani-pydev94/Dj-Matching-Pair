from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from profiles.services import get_profile_completion

def landing_view(request):
    return render(request, 'pages/landing.html')

@login_required
def home_view(request):
    profile_pct = get_profile_completion(request.user)
    questionnaire_done = hasattr(request.user, 'profile') and bool(request.user.profile.bio)
    top_matches = []
    try:
        from matching.models import Match
        top_matches = list(request.user.matches_from.select_related('user_b__profile').all()[:3])
    except Exception:
        top_matches = []
    communities = []
    try:
        from communities.models import Community
        communities = list(Community.objects.all()[:3])
    except Exception:
        pass
    events = []
    try:
        from events.models import Event
        events = list(Event.objects.all().order_by('start')[:3])
    except Exception:
        pass
    return render(request, 'pages/home.html', {
        'profile_pct': profile_pct,
        'questionnaire_done': questionnaire_done,
        'top_matches': top_matches,
        'communities': communities,
        'events': events,
    })

urlpatterns = [
    path('', landing_view, name='landing'),
    path('home/', home_view, name='home'),
]
