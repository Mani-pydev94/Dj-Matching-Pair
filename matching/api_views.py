from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from connections.models import Connection
from .compatibility import MIN_MATCH_SCORE
from .services import excluded_ids, is_discoverable, score_match

User = get_user_model()


class MatchesAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        candidates = User.objects.filter(
            is_active=True,
            profile__is_public=True,
            profile__questionnaire_completed=True,
        ).exclude(id__in=excluded_ids(request.user)).select_related('profile')
        min_score = float(request.query_params.get('min_score', MIN_MATCH_SCORE))
        university = request.query_params.get('university')
        city = request.query_params.get('city')
        if university:
            candidates = candidates.filter(profile__university__iexact=university)
        if city:
            candidates = candidates.filter(profile__city__iexact=city)
        connections = Connection.objects.filter(
            Q(requester=request.user) | Q(recipient=request.user),
        )
        connection_by_user = {}
        for connection in connections:
            other_id = connection.recipient_id if connection.requester_id == request.user.id else connection.requester_id
            current = connection_by_user.get(other_id)
            if current is None or (
                connection.status in ('ACCEPTED', 'CONNECTED') and
                current.status not in ('ACCEPTED', 'CONNECTED')
            ):
                connection_by_user[other_id] = connection
        results = []
        for student in candidates:
            breakdown = score_match(request.user, student)
            if not is_discoverable(request.user, student, breakdown, min_score):
                continue
            connection = connection_by_user.get(student.id)
            full_profile = connection is not None and connection.status in ('ACCEPTED', 'CONNECTED')
            safe_breakdown = breakdown if full_profile else {
                'overall_score': breakdown['overall_score'],
                'reasons': ['Recommended by AI compatibility'],
                'shared_interests': [],
            }
            results.append({
                'user_id': student.id,
                'display_name': student.get_full_name() or student.email,
                # Photos are unlocked only after an accepted connection.
                'profile_photo': (
                    request.build_absolute_uri(student.profile.photo.url)
                    if student.profile.photo and full_profile else None
                ),
                'connection_id': str(connection.id) if connection else None,
                'connection_status': connection.status if connection else 'NONE',
                'university': student.profile.university if full_profile else '',
                'field_of_study': student.profile.major if full_profile else '',
                'is_private': not full_profile,
                **safe_breakdown,
            })
        results.sort(key=lambda item: item['overall_score'], reverse=True)
        return Response({'results': results})


class CompatibilityAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, user_id):
        student = User.objects.filter(id=user_id, is_active=True).select_related('profile').first()
        if not student or student == request.user:
            return Response({'detail': 'Student not found.'}, status=404)
        if student.id in excluded_ids(request.user):
            return Response({'detail': 'Student not found.'}, status=404)
        return Response(score_match(request.user, student))
