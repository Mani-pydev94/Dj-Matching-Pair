from django.conf import settings
from django.db.models import Q

from connections.models import Connection
from .compatibility import calculate_compatibility


def normalized_university(profile):
    return (getattr(profile, 'university', '') or '').strip().casefold()


def matching_settings():
    return getattr(settings, 'MATCHING', {})


def score_match(user, candidate):
    """Return questionnaire-primary score with transparent profile factors."""
    questionnaire = calculate_compatibility(user, candidate)
    cfg = matching_settings()
    q_weight = float(cfg.get('QUESTIONNAIRE_WEIGHT', 0.70))
    factors = {}
    a = getattr(user, 'profile', None)
    b = getattr(candidate, 'profile', None)
    factors['interests'] = 100 if a and b and set(x.strip().lower() for x in a.interests.split(',') if x.strip()) & set(x.strip().lower() for x in b.interests.split(',') if x.strip()) else 0
    factors['university'] = 100 if a and b and normalized_university(a) and normalized_university(a) == normalized_university(b) else 0
    factors['city'] = 100 if a and b and a.city and a.city.casefold() == b.city.casefold() else 0
    weights = cfg.get('PROFILE_WEIGHTS', {'interests': .15, 'university': .10, 'city': .05})
    total_weight = sum(float(weight) for weight in weights.values()) or 1
    profile_score = sum(factors[key] * float(weight) for key, weight in weights.items()) / total_weight
    overall = round(questionnaire['overall_score'] * q_weight + profile_score * (1 - q_weight))
    reasons = list(questionnaire['reasons'])
    if factors['university'] == 100:
        reasons.append('Same university')
    return {**questionnaire, 'overall_score': max(0, min(100, overall)),
            'reasons': reasons, 'profile_factors': factors,
            'questionnaire_score': questionnaire['overall_score']}


def is_discoverable(user, candidate, breakdown, minimum_score=None):
    """Allow strong matches or discovery within the same university."""
    cfg = matching_settings()
    minimum = float(minimum_score if minimum_score is not None else cfg.get('MINIMUM_SCORE', 75))
    if breakdown['overall_score'] >= minimum:
        return True
    user_profile = getattr(user, 'profile', None)
    candidate_profile = getattr(candidate, 'profile', None)
    same_university = (
        user_profile and candidate_profile and normalized_university(user_profile) and
        normalized_university(user_profile) == normalized_university(candidate_profile)
    )
    return bool(same_university)


def blocked_user_ids(user):
    return Connection.objects.filter(
        Q(requester=user, status='BLOCKED') | Q(recipient=user, status='BLOCKED')
    ).values_list('recipient_id', 'requester_id')


def excluded_ids(user):
    ids = {user.id}
    for recipient, requester in blocked_user_ids(user):
        ids.update((recipient, requester))
    return ids
