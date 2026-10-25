from django.db.models import Count, Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Question, QuestionOption, QuestionResponse, QuestionnaireCategory
from .serializers import CategorySerializer, QuestionSerializer, ResponseSerializer
from .services import mark_questionnaire_completed, questionnaire_progress
from .summary import (
    InsightGenerationError,
    generate_category_summaries,
    get_questionnaire_summary,
    gemini_is_configured,
)


class QuestionnaireQuestionsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        questions = Question.objects.filter(is_active=True)
        category_slug = request.query_params.get('category')
        if category_slug:
            questions = questions.filter(category_ref__slug=category_slug)
        questions = questions.order_by(
            'category_ref__display_order', 'category_ref__name', 'order', 'id',
        ).prefetch_related(
            Prefetch('options', queryset=QuestionOption.objects.filter(is_active=True)),
            'category_ref',
        )
        return Response(QuestionSerializer(questions, many=True).data)


class QuestionnaireCategoriesAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        categories = QuestionnaireCategory.objects.filter(is_active=True).annotate(
            question_count=Count('questions', filter=None),
        )
        answers = set(QuestionResponse.objects.filter(user=request.user).values_list('question_id', flat=True))
        data = CategorySerializer(categories, many=True).data
        for item in data:
            question_ids = set(Question.objects.filter(category_ref_id=item['id'], is_active=True).values_list('id', flat=True))
            item['answered_count'] = len(question_ids & answers)
        return Response(data)


class QuestionnaireProgressAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(questionnaire_progress(request.user))


class QuestionnaireResponsesAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        responses = QuestionResponse.objects.filter(user=request.user).prefetch_related('selected_options')
        return Response(ResponseSerializer(responses, many=True).data)

    def post(self, request):
        serializer = ResponseSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data['question']
        if not question.is_active:
            return Response({'detail': 'This question is no longer active.'}, status=status.HTTP_400_BAD_REQUEST)
        response = serializer.save()
        return Response(ResponseSerializer(response).data, status=status.HTTP_201_CREATED)


class QuestionnaireCompleteAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if not mark_questionnaire_completed(request.user):
            progress = questionnaire_progress(request.user)
            return Response({'detail': 'Complete all required questions first.', 'progress': progress}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'completed': True,
            'progress': questionnaire_progress(request.user),
        })


class QuestionnaireSummaryAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not questionnaire_progress(request.user)['is_complete']:
            return Response(
                {'detail': 'Complete all required questions to view your summary.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        summary = get_questionnaire_summary(request.user)
        profile = getattr(request.user, 'profile', None)
        summary['ai_consent'] = bool(
            profile and profile.questionnaire_ai_consent
        )
        return Response(summary)


class QuestionnaireSummaryInsightsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if request.data.get('consent') is not True:
            return Response(
                {'detail': 'Confirm before sending your answers to Gemini.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile = getattr(request.user, 'profile', None)
        if not profile or profile.questionnaire_ai_consent is not True:
            return Response(
                {'detail': 'Opt in to AI reflections before sending your answers to Gemini.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            result = generate_category_summaries(request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except InsightGenerationError as exc:
            status_code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if not gemini_is_configured()
                else status.HTTP_502_BAD_GATEWAY
            )
            return Response({'detail': str(exc)}, status=status_code)
        return Response(result)
