from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from profiles.models import Profile
from .services import mark_questionnaire_completed


@login_required
def questionnaire_intro(request):
    if request.method == 'POST':
        consent = request.POST.get('ai_consent')
        if consent not in ('yes', 'no'):
            return render(request, 'questionnaire/intro.html', {
                'consent_error': 'Choose whether to enable automatic AI reflections before continuing.',
            })
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.questionnaire_ai_consent = consent == 'yes'
        profile.save(update_fields=('questionnaire_ai_consent', 'updated_at'))
        return redirect('questionnaire_hub')
    return render(request, 'questionnaire/intro.html')


@login_required
def questionnaire_hub(request):
    if mark_questionnaire_completed(request.user):
        return redirect('questionnaire_summary')
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.questionnaire_ai_consent is None:
        return redirect('questionnaire_intro')
    return render(request, 'questionnaire/hub.html')


@login_required
def questionnaire_questions(request):
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.questionnaire_ai_consent is None:
        return redirect('questionnaire_intro')
    return render(request, 'questionnaire/questions.html')


@login_required
def questionnaire_summary(request):
    if not mark_questionnaire_completed(request.user):
        return redirect('questionnaire_hub')
    return render(request, 'questionnaire/summary.html')


urlpatterns = [
    path('intro/', questionnaire_intro, name='questionnaire_intro'),
    path('hub/', questionnaire_hub, name='questionnaire_hub'),
    path('questions/', questionnaire_questions, name='questionnaire_questions'),
    path('summary/', questionnaire_summary, name='questionnaire_summary'),
]
