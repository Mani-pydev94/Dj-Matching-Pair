from django.urls import path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def questionnaire_intro(request):
    return render(request, 'questionnaire/intro.html')


@login_required
def questionnaire_hub(request):
    return render(request, 'questionnaire/hub.html')


@login_required
def questionnaire_questions(request):
    return render(request, 'questionnaire/questions.html')

urlpatterns = [
    path('intro/', questionnaire_intro, name='questionnaire_intro'),
    path('hub/', questionnaire_hub, name='questionnaire_hub'),
    path('questions/', questionnaire_questions, name='questionnaire_questions'),
]
