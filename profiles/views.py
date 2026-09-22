from copy import copy

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import redirect, render

from matching.models import Match
from connections.models import Connection
from django.db.models import Q

from .forms import ProfileSetupForm
from .models import Profile
from .services import can_view_full_profile, get_profile_completion


@login_required
def profile_setup(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileSetupForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            if not profile.is_public:
                profile.is_public = True
                profile.save(update_fields=('is_public', 'updated_at'))
            messages.success(request, 'Your profile has been saved.')
            return redirect('home')
    else:
        form = ProfileSetupForm(instance=profile, user=request.user)

    return render(request, 'profiles/setup.html', {
        'form': form,
        'profile': profile,
        'profile_pct': get_profile_completion(request.user),
    })


@login_required
def my_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'profiles/my_profile.html', {
        'profile': profile,
        'profile_pct': get_profile_completion(request.user),
    })


@login_required
def edit_profile(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileSetupForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            if not profile.is_public:
                profile.is_public = True
                profile.save(update_fields=('is_public', 'updated_at'))
            messages.success(request, 'Your profile changes have been saved.')
            return redirect('profiles:my_profile')
    else:
        form = ProfileSetupForm(instance=profile, user=request.user)

    return render(request, 'profiles/edit_profile.html', {
        'form': form,
        'profile': profile,
        'profile_pct': get_profile_completion(request.user),
    })


@login_required
def student_profile(request, user_id):
    user_model = get_user_model()
    student = user_model.objects.select_related('profile').filter(id=user_id).first()
    if not student or not hasattr(student, 'profile'):
        raise Http404

    profile = student.profile
    is_connected = can_view_full_profile(request.user, student)
    visible_profile = profile
    if student != request.user and not is_connected:
        visible_profile = copy(profile)
        for field in ('photo', 'age', 'city', 'gender', 'languages', 'bio', 'university', 'major', 'year', 'interests'):
            setattr(visible_profile, field, '' if field != 'photo' else None)
    connection = Connection.objects.filter(
        Q(requester=request.user, recipient=student) |
        Q(requester=student, recipient=request.user)
    ).first()

    match = None
    insight = None
    if is_connected:
        match = Match.objects.filter(
            user_a=request.user, user_b=student,
        ).first() or Match.objects.filter(
            user_a=student, user_b=request.user,
        ).first()
        insight = getattr(match, 'insight', None) if match else None

    return render(request, 'profiles/student_profile.html', {
        'student': student,
        'profile': visible_profile,
        'match': match,
        'insight': insight,
        'connection': connection,
        'is_connected': is_connected,
        'can_chat': is_connected,
        'is_private_preview': student != request.user and not is_connected,
    })
