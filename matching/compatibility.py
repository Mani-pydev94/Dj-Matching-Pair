from collections import defaultdict

from questionnaire.models import QuestionResponse, QuestionnaireCategory

CATEGORY_WEIGHTS = {
    'values': 1 / 6,
    'learning-style': 1 / 6,
    'communication': 1 / 6,
    'career-goals': 1 / 6,
    'lifestyle': 1 / 6,
    'interests': 1 / 6,
}
MIN_MATCH_SCORE = 75


def _response_map(user):
    return {
        response.question_id: response
        for response in QuestionResponse.objects.filter(user=user).order_by(
            'question__category', 'question__order',
        ).prefetch_related('selected_options', 'question__category_ref')
    }


def _similarity(first, second):
    first_options = {option.option_value for option in first.selected_options.all()}
    second_options = {option.option_value for option in second.selected_options.all()}
    first_other = set(first.other_text.strip().lower().split())
    second_other = set(second.other_text.strip().lower().split())
    if first_options or second_options or first_other or second_other:
        first_answers = {f'option:{value}' for value in first_options}
        first_answers.update(f'other-word:{word}' for word in first_other)
        second_answers = {f'option:{value}' for value in second_options}
        second_answers.update(f'other-word:{word}' for word in second_other)
        union = first_answers | second_answers
        return 100.0 * len(first_answers & second_answers) / len(union) if union else 0.0
    if first.value.isdigit() and second.value.isdigit():
        return max(0.0, 100.0 - abs(int(first.value) - int(second.value)) * 25.0)
    return 100.0 if first.value.strip().lower() == second.value.strip().lower() else 0.0


def _importance_weight(first, second):
    weights = {
        QuestionResponse.Importance.NOT_VERY_IMPORTANT: 0.5,
        QuestionResponse.Importance.NEUTRAL: 1.0,
        QuestionResponse.Importance.MOST_IMPORTANT: 2.0,
    }
    return (weights[first.importance] + weights[second.importance]) / 2


def calculate_compatibility(user_a, user_b):
    first = _response_map(user_a)
    second = _response_map(user_b)
    category_scores = defaultdict(lambda: {'weighted_total': 0.0, 'total_weight': 0.0})
    shared_interests = set()
    for question_id, response_a in first.items():
        response_b = second.get(question_id)
        if not response_b:
            continue
        category = response_a.question.category_ref.slug if response_a.question.category_ref else response_a.question.category
        weight = _importance_weight(response_a, response_b)
        category_scores[category]['weighted_total'] += _similarity(response_a, response_b) * weight
        category_scores[category]['total_weight'] += weight
    scores = {
        category: round(values['weighted_total'] / values['total_weight'])
        for category, values in category_scores.items()
        if values['total_weight']
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
        'importance_note': 'Question similarity is weighted by the average importance both people assigned.',
    }


def calculate_compatibility_analysis(user_a, user_b):
    first = _response_map(user_a)
    second = _response_map(user_b)
    question_scores = []
    category_scores = defaultdict(lambda: {'weighted_total': 0.0, 'total_weight': 0.0})

    for question_id, response_a in first.items():
        response_b = second.get(question_id)
        if not response_b:
            continue
        category = response_a.question.category_ref
        category_key = category.slug if category else response_a.question.category
        similarity = _similarity(response_a, response_b)
        importance_weight = _importance_weight(response_a, response_b)
        category_scores[category_key]['weighted_total'] += similarity * importance_weight
        category_scores[category_key]['total_weight'] += importance_weight
        question_scores.append({
            'question': response_a.question.text,
            'category': category.name if category else response_a.question.category.replace('-', ' ').title(),
            'similarity': round(similarity),
            'importance_weight': importance_weight,
        })

    scores = {
        category: round(values['weighted_total'] / values['total_weight'])
        for category, values in category_scores.items()
        if values['total_weight']
    }
    category_names = {
        category.slug: category.name
        for category in QuestionnaireCategory.objects.filter(
            slug__in=CATEGORY_WEIGHTS,
        )
    }
    categories = [
        {
            'name': category_names.get(key, key.replace('-', ' ').title()),
            'score': scores.get(key, 0),
        }
        for key in CATEGORY_WEIGHTS
    ]
    most_important = [
        item for item in question_scores if item['importance_weight'] > 1
    ]
    least_important = [
        item for item in question_scores if item['importance_weight'] < 1
    ]

    def group_score(items):
        return round(sum(item['similarity'] for item in items) / len(items)) if items else None

    from .services import score_match

    return {
        'overall_score': score_match(user_a, user_b)['overall_score'],
        'categories': categories,
        'most_important_questions': most_important,
        'most_important_similarity': group_score(most_important),
        'least_important_questions': least_important,
        'least_important_similarity': group_score(least_important),
    }
