from django.urls import path

from .api_views import (
    QuestionnaireCategoriesAPIView,
    QuestionnaireCompleteAPIView,
    QuestionnaireProgressAPIView,
    QuestionnaireQuestionsAPIView,
    QuestionnaireResponsesAPIView,
)

urlpatterns = [
    path('', QuestionnaireQuestionsAPIView.as_view(), name='api_questionnaire'),
    path('categories/', QuestionnaireCategoriesAPIView.as_view(), name='api_questionnaire_categories'),
    path('questions/', QuestionnaireQuestionsAPIView.as_view(), name='api_questionnaire_questions'),
    path('progress/', QuestionnaireProgressAPIView.as_view(), name='api_questionnaire_progress'),
    path('responses/', QuestionnaireResponsesAPIView.as_view(), name='api_questionnaire_responses'),
    path('complete/', QuestionnaireCompleteAPIView.as_view(), name='api_questionnaire_complete'),
]
