from collections import defaultdict

from questionnaire.models import QuestionResponse

CATEGORY_WEIGHTS = {
    'values': 0.20,
    'learning-style': 0.20,
    'communication': 0.15,
    'career-goals': 0.20,
    'lifestyle': 0.10,
    'interests': 0.15,
}
MIN_MATCH_SCORE = 75


def _response_map(user):
    return {
        response.question_id: response
        for response in QuestionResponse.objects.filter(user=user).prefetch_related('selected_options', 'question__category_ref')
    }


def _similarity(first, second):
    first_options = {option.option_value for option in first.selected_options.all()}
    second_options = {option.option_value for option in second.selected_options.all()}
    if first_options or second_options:
        union = first_options | second_options
        return 100.0 * len(first_options & second_options) / len(union) if union else 0.0
    if first.value.isdigit() and second.value.isdigit():
        return max(0.0, 100.0 - abs(int(first.value) - int(second.value)) * 25.0)
    return 100.0 if first.value.strip().lower() == second.value.strip().lower() else 0.0


def calculate_compatibility(user_a, user_b):
    first = _response_map(user_a)
    second = _response_map(user_b)
    category_scores = defaultdict(list)
    shared_interests = set()
    for question_id, response_a in first.items():
        response_b = second.get(question_id)
        if not response_b:
            continue
        category = response_a.question.category_ref.slug if response_a.question.category_ref else response_a.question.category
        category_scores[category].append(_similarity(response_a, response_b))
    scores = {
        category: round(sum(values) / len(values)) if values else 0
        for category, values in category_scores.items()
    }
    overall = round(sum(scores.get(category, 0) * weight for category, weight in CATEGORY_WEIGHTS.items()))
    interests_a = {item.strip().lower() for item in user_a.profile.interests.split(',') if item.strip()} if hasattr(user_a, 'profile') else set()
    interests_b = {item.strip().lower() for item in user_b.profile.interests.split(',') if item.strip()} if hasattr(user_b, 'profile') else set()
    shared_interests = sorted(interests_a & interests_b)
    reasons = []
    if scores.get('learning-style', 0) >= 75:
        reasons.append('Similar learning style')
    if scores.get('career-goals', 0) >= 75:
        reasons.append('Aligned career goals')
    if shared_interests:
        reasons.append(f"Shared interests: {', '.join(shared_interests[:3])}")
    return {
        'overall_score': max(0, min(100, overall)),
        'categories': {key: scores.get(key, 0) for key in CATEGORY_WEIGHTS},
        'shared_interests': shared_interests,
        'reasons': reasons,
    }
