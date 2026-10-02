from collections import defaultdict

from questionnaire.models import QuestionResponse, QuestionnaireCategory

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
    category_scores = defaultdict(list)
    question_similarities = []
    shared_interests = set()
    for question_id, response_a in first.items():
        response_b = second.get(question_id)
        if not response_b:
            continue
        category = response_a.question.category_ref.slug if response_a.question.category_ref else response_a.question.category
        similarity = _similarity(response_a, response_b)
        category_scores[category].append(similarity)
        question_similarities.append(similarity)
    scores = {
        category: round(sum(similarities) / len(similarities))
        for category, similarities in category_scores.items()
    }
    overall = round(sum(question_similarities) / len(question_similarities)) if question_similarities else 0
    interests_a = {item.strip().lower() for item in user_a.profile.interests.split(',') if item.strip()} if hasattr(user_a, 'profile') else set()
    interests_b = {item.strip().lower() for item in user_b.profile.interests.split(',') if item.strip()} if hasattr(user_b, 'profile') else set()
    shared_interests = sorted(interests_a & interests_b)
    reasons = []
    for category in QuestionnaireCategory.objects.filter(is_active=True).order_by('display_order', 'name'):
        if scores.get(category.slug, 0) >= 75:
            reasons.append(f'Similar {category.name.casefold()}')
    if shared_interests:
        reasons.append(f"Shared interests: {', '.join(shared_interests[:3])}")
    return {
        'overall_score': max(0, min(100, overall)),
        'categories': {
            category.slug: scores.get(category.slug, 0)
            for category in QuestionnaireCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        },
        'shared_interests': shared_interests,
        'reasons': reasons,
        'importance_note': 'Every shared question contributes equally to the questionnaire score.',
    }


def calculate_compatibility_analysis(user_a, user_b):
    first = _response_map(user_a)
    second = _response_map(user_b)
    question_scores = []
    category_scores = defaultdict(list)

    for question_id, response_a in first.items():
        response_b = second.get(question_id)
        if not response_b:
            continue
        category = response_a.question.category_ref
        category_key = category.slug if category else response_a.question.category
        similarity = _similarity(response_a, response_b)
        category_scores[category_key].append(similarity)
        importance_weight = _importance_weight(response_a, response_b)
        question_scores.append({
            'question': response_a.question.text,
            'category': category.name if category else response_a.question.category.replace('-', ' ').title(),
            'similarity': round(similarity),
            'importance_weight': importance_weight,
        })

    scores = {
        category: round(sum(similarities) / len(similarities))
        for category, similarities in category_scores.items()
    }
    categories = [
        {
            'name': category.name,
            'score': scores.get(category.slug, 0),
        }
        for category in QuestionnaireCategory.objects.filter(is_active=True).order_by('display_order', 'name')
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
