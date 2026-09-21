from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def matches_ready(request):
    return render(request, 'matching/matches_ready.html')


@login_required
def explore_matches(request):
    return render(request, 'matching/explore_matches.html')

urlpatterns = [
    path('ready/', matches_ready, name='matches_ready'),
    path('explore/', explore_matches, name='explore_matches'),
]
