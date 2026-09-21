from django.db.models import Count, Prefetch
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Question, QuestionOption, QuestionResponse, QuestionnaireCategory
from .serializers import CategorySerializer, QuestionSerializer, ResponseSerializer
from .services import questionnaire_progress
from profiles.models import Profile


class QuestionnaireQuestionsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        questions = Question.objects.filter(is_active=True).prefetch_related(
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
        progress = questionnaire_progress(request.user)
        if not progress['is_complete']:
            return Response({'detail': 'Complete all required questions first.', 'progress': progress}, status=status.HTTP_400_BAD_REQUEST)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.questionnaire_completed = True
        update_fields = ['questionnaire_completed', 'updated_at']
        if not profile.is_public:
            profile.is_public = True
            update_fields.append('is_public')
        profile.save(update_fields=update_fields)
        return Response({'completed': True, 'progress': progress})
