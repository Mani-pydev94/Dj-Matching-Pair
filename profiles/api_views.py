from django.contrib.auth import get_user_model
from django.db.models import Q
from PIL import Image, UnidentifiedImageError
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Message
from connections.models import Connection
from questionnaire.models import QuestionResponse

from .models import Profile
from .serializers import (
    ProfileSerializer,
    ProfileStatsSerializer,
    ProfileStrengthSerializer,
    PublicStudentProfileSerializer,
    ProfilePreviewSerializer,
)
from .services import can_view_full_profile, get_profile_strength

User = get_user_model()
MAX_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_PHOTO_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def get_or_create_profile(user):
    return Profile.objects.get_or_create(user=user)[0]


class MyProfileAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (SessionAuthentication,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request):
        return Response(ProfileSerializer(get_or_create_profile(request.user), context={'request': request}).data)

    def post(self, request):
        profile = get_or_create_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=False, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = get_or_create_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class MyProfilePhotoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def patch(self, request):
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'photo': 'A photo file is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if photo.content_type not in ALLOWED_PHOTO_TYPES:
            return Response({'photo': 'Only JPG, JPEG, PNG, and WEBP images are allowed.'}, status=status.HTTP_400_BAD_REQUEST)
        if photo.size > MAX_PHOTO_SIZE:
            return Response({'photo': 'The image must be 5 MB or smaller.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            image = Image.open(photo)
            image.verify()
        except (UnidentifiedImageError, OSError):
            return Response({'photo': 'Upload a valid image file.'}, status=status.HTTP_400_BAD_REQUEST)
        photo.seek(0)
        profile = get_or_create_profile(request.user)
        profile.photo = photo
        profile.save(update_fields=('photo', 'updated_at'))
        return Response(ProfileSerializer(profile, context={'request': request}).data)

    def delete(self, request):
        profile = get_or_create_profile(request.user)
        if profile.photo:
            profile.photo.delete(save=False)
            profile.photo = None
            profile.save(update_fields=('photo', 'updated_at'))
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyProfileStrengthAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(ProfileStrengthSerializer(get_profile_strength(request.user)).data)


class MyProfileStatsAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        data = {
            'communities_count': 0,
            'chats_count': Message.objects.filter(Q(sender=user) | Q(recipient=user)).count(),
            'events_count': 0,
            'answers_count': QuestionResponse.objects.filter(user=user).count(),
        }
        try:
            data['communities_count'] = user.community_memberships.count()
        except AttributeError:
            pass
        return Response(ProfileStatsSerializer(data).data)


class PublicStudentProfileAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, user_id):
        student = User.objects.select_related('profile').filter(id=user_id).first()
        if not student or not hasattr(student, 'profile'):
            return Response({'detail': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)
        profile = student.profile
        allowed = can_view_full_profile(request.user, student)
        if student != request.user and not allowed:
            return Response(ProfilePreviewSerializer(profile, context={'request': request}).data)
        return Response(PublicStudentProfileSerializer(profile, context={'request': request}).data)
