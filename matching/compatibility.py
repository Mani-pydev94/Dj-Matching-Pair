import hashlib
import json
from collections import defaultdict

from questionnaire.models import (
    Question,
    QuestionResponse,
    QuestionnaireCategory,
)

MIN_MATCH_SCORE = 10
SIMILARITY_WEIGHT = 0.6
COMPLEMENT_WEIGHT = 0.4


def _response_map(user):
    return {
        response.question_id: response
        for response in QuestionResponse.objects.filter(user=user).order_by(
            'question__category', 'question__order',
        ).prefetch_related('selected_options', 'question__category_ref', 'question__options')
    }


def _similarity(first, second):
    """0-100: how much the two answers line up (legacy behaviour)."""
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


def _complementarity(first, second, question):
    """0-100: how well two style answers sit on the same pole, or None.

    Options act as poles on a spectrum ordered by display_order (first = pole
    A, last = pole B). For a style question, *same-side* answers are the good
    outcome: two planners click more with each other than a planner with an
    improviser. So the closer together the two answers sit, the more they
    balance each other. Same pole = 100, exact opposites = 0.
    """
    options = sorted(question.options.all(), key=lambda o: o.display_order)
    if len(options) < 2:
        return None
    rank = {o.option_value: i for i, o in enumerate(options)}
    first_values = [v for v in first.selected_options.values_list('option_value', flat=True) if v in rank]
    second_values = [v for v in second.selected_options.values_list('option_value', flat=True) if v in rank]
    if not first_values or not second_values:
        return None
    if len(options) > 2:
        # Average pole position so multi-option spectres stay balanced.
        first_pos = sum(rank[v] for v in first_values) / len(first_values)
        second_pos = sum(rank[v] for v in second_values) / len(second_values)
    else:
        first_pos = rank[first_values[0]]
        second_pos = rank[second_values[0]]
    span = len(options) - 1
    distance = abs(first_pos - second_pos) / span
    return round(100.0 * (1.0 - distance))


def _is_blank(response):
    return not response.selected_options.exists() and not response.value.strip()


def _question_pair_score(response_a, response_b):
    """Contribution of one shared question to the match formula.

    Blank or free-text-only answers carry no shared data: they contribute 0
    and are marked 'blank' so the story selectors skip them.
    """
    similarity = _similarity(response_a, response_b)
    question = response_a.question
    if _is_blank(response_a) or _is_blank(response_b):
        return {'kind': question.score_type, 'contribution': 0.0, 'similarity': 0.0, 'blank': True}
    if question.score_type == Question.ScoreType.COMPLEMENTARY:
        complement = _complementarity(response_a, response_b, question)
        if complement is None:
            return {'kind': 'COMPLEMENTARY', 'contribution': 0.0, 'similarity': 0.0, 'blank': True}
        return {'kind': 'COMPLEMENTARY', 'contribution': complement, 'similarity': similarity}
    return {'kind': 'SIMILARITY', 'contribution': similarity, 'similarity': similarity}


def _category_reflection(name, score, has_shared_answers=True):
    topic = name.casefold()
    if not has_shared_answers:
        return (
            f"There is not enough shared questionnaire data about {topic} to "
            'compare yet. More completed answers can make this picture clearer.'
        )
    if score >= 80:
        return (
            f"You have strong common ground in {topic}. Compare what that shared "
            'ground means to each of you and where your individual perspectives add something new.'
        )
    if score >= 55:
        return (
            f"You share some common ground in {topic}, with room to discover "
            "more. A thoughtful conversation can reveal what matters most to each of you."
        )
    return (
        f"Your perspectives on {topic} may differ. That makes curiosity and "
        'open conversation especially valuable as you get to know each other.'
    )


def _compatibility_core(user_a, user_b):
    first = _response_map(user_a)
    second = _response_map(user_b)
    category_scores = defaultdict(list)
    similarity_pool = []
    complement_pool = []
    pairs = []
    for question_id, response_a in first.items():
        response_b = second.get(question_id)
        if not response_b:
            continue
        pair = _question_pair_score(response_a, response_b)
        contribution = pair['contribution']
        category_key = (
            response_a.question.category_ref.slug
            if response_a.question.category_ref else response_a.question.category
        )
        category_scores[category_key].append(contribution)
        if pair.get('blank'):
            continue
        pairs.append((response_a, response_b, pair))
        (similarity_pool if pair['kind'] == 'SIMILARITY' else complement_pool).append(contribution)

    def pool_average(pool):
        return round(sum(pool) / len(pool)) if pool else 0

    similarity_score = pool_average(similarity_pool)
    complement_score = pool_average(complement_pool)
    if similarity_pool and complement_pool:
        overall = round(SIMILARITY_WEIGHT * similarity_score + COMPLEMENT_WEIGHT * complement_score)
    elif similarity_pool:
        overall = similarity_score
    elif complement_pool:
        overall = complement_score
    else:
        overall = 0

    return {
        'pairs': pairs,
        'category_scores': category_scores,
        'similarity_score': similarity_score,
        'complement_score': complement_score,
        'overall': overall,
    }


def calculate_compatibility(user_a, user_b):
    """Public per-pair score: 0.6 x similarity + 0.4 x complementarity."""
    core = _compatibility_core(user_a, user_b)
    categories = {
        key: round(sum(scores) / len(scores)) for key, scores in core['category_scores'].items()
    }
    interests_a = {
        item.strip().lower() for item in user_a.profile.interests.split(',') if item.strip()
    } if hasattr(user_a, 'profile') else set()
    interests_b = {
        item.strip().lower() for item in user_b.profile.interests.split(',') if item.strip()
    } if hasattr(user_b, 'profile') else set()
    shared_interests = sorted(interests_a & interests_b)
    reasons = []
    for category in QuestionnaireCategory.objects.filter(is_active=True).order_by('display_order', 'name'):
        if categories.get(category.slug, 0) >= 75:
            reasons.append(f'Similar {category.name.casefold()}')
    if shared_interests:
        reasons.append(f"Shared interests: {', '.join(shared_interests[:3])}")
    return {
        'overall_score': max(0, min(100, core['overall'])),
        'same_wavelength': core['similarity_score'],
        'balance_each_other': core['complement_score'],
        'categories': {
            category.slug: categories.get(category.slug, 0)
            for category in QuestionnaireCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        },
        'shared_interests': shared_interests,
        'reasons': reasons,
        'importance_note': 'Match = 60% same-wavelength similarity + 40% complementary balance.',
    }


def _importance_weight(first, second):
    weights = {
        QuestionResponse.Importance.NOT_VERY_IMPORTANT: 0.5,
        QuestionResponse.Importance.NEUTRAL: 1.0,
        QuestionResponse.Importance.MOST_IMPORTANT: 2.0,
    }
    return (weights[first.importance] + weights[second.importance]) / 2


def _pair_answers(response):
    options = sorted(response.selected_options.all(), key=lambda o: o.display_order)
    texts = [option.option_text for option in options]
    if response.other_text.strip():
        texts.append(response.other_text.strip())
    return texts


def _category_name(question):
    return question.category_ref.name if question.category_ref else question.category


def _shared_dna(pairs, limit=3):
    exact = [pair for pair in pairs if pair[2]['kind'] == 'SIMILARITY' and pair[2]['similarity'] == 100]
    pool = exact or [pair for pair in pairs if pair[2]['similarity'] >= 50]
    pool.sort(key=lambda pair: (-_importance_weight(pair[0], pair[1]),
                                pair[0].question.category_ref.display_order if pair[0].question.category_ref else 0,
                                pair[0].question.order))
    items = []
    for response_a, response_b, pair in pool[:limit]:
        items.append({
            'question': response_a.question.text,
            'category': _category_name(response_a.question),
            'answers': _pair_answers(response_a),
            'shared': bool(exact),
        })
    return items


def _sparks(pairs, limit=2):
    balanced = [pair for pair in pairs if pair[2]['kind'] == 'COMPLEMENTARY' and pair[2]['contribution'] >= 60]
    balanced.sort(key=lambda pair: (-pair[2]['contribution'], -_importance_weight(pair[0], pair[1])))
    items = []
    for response_a, response_b, pair in balanced[:limit]:
        items.append({
            'question': response_a.question.text,
            'category': _category_name(response_a.question),
            'balance': pair['contribution'],
            'your_answer': _pair_answers(response_a),
        })
    return items


def _mystery_match(pairs):
    """A shared answer neither rated as most important — the surprising one."""
    candidates = [
        pair for pair in pairs
        if pair[2]['kind'] == 'SIMILARITY' and pair[2]['similarity'] == 100
        and pair[0].importance != QuestionResponse.Importance.MOST_IMPORTANT
    ]
    if not candidates:
        candidates = [pair for pair in pairs if pair[2]['kind'] == 'SIMILARITY' and pair[2]['similarity'] == 100]
    if not candidates:
        return None
    candidates.sort(key=lambda pair: _importance_weight(pair[0], pair[1]))
    response_a, _, _ = candidates[0]
    question = response_a.question
    return {
        'question': question.text,
        'category': _category_name(question),
        'answers': _pair_answers(response_a),
    }


def _conversation_starters(pairs, limit=3):
    candidates = [pair for pair in pairs if pair[2]['similarity'] == 100]
    candidates.sort(key=lambda pair: (-_importance_weight(pair[0], pair[1]),
                                       pair[0].question.category_ref.display_order if pair[0].question.category_ref else 0,
                                       pair[0].question.order))
    return [
        {
            'question': pair[0].question.text,
            'category': _category_name(pair[0].question),
            'answers': _pair_answers(pair[0]),
        }
        for pair in candidates[:limit]
    ]


def _guess_game(pairs):
    """A quiz about one of their answers, built from a shared question."""
    candidates = [
        pair for pair in pairs
        if pair[2]['kind'] == 'SIMILARITY' and pair[2]['similarity'] == 100
        and len(pair[0].question.options.all()) >= 2
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda pair: _importance_weight(pair[0], pair[1]))
    response_a, response_b, _ = candidates[0]
    question = response_a.question
    options = sorted(question.options.all(), key=lambda o: o.display_order)
    their_values = list(response_b.selected_options.values_list('option_value', flat=True))
    your_values = list(response_a.selected_options.values_list('option_value', flat=True))
    their_index = next((i for i, o in enumerate(options) if o.option_value in their_values), 0)
    your_index = next((i for i, o in enumerate(options) if o.option_value in your_values), their_index)
    return {
        'question': question.text,
        'category': _category_name(question),
        'options': [o.option_text for o in options],
        'their_index': their_index,
        'your_index': your_index,
    }


def _answers_fingerprint(user):
    rows = []
    for response in QuestionResponse.objects.filter(user=user).order_by('question__question_key'):
        rows.append((
            response.question.question_key,
            response.value,
            response.importance,
            sorted(o.option_value for o in response.selected_options.all()),
            response.other_text.strip().lower(),
        ))
    source = json.dumps(rows, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


def calculate_compatibility_analysis(user_a, user_b):
    """Full 'Why You Two Click' analysis.

    user_a is the *viewer*. Answer details are only exposed for shared
    answers, so a private preview never leaks specifics the viewer shouldn't
    see.
    """
    core = _compatibility_core(user_a, user_b)
    pairs = core['pairs']
    pairs.sort(key=lambda pair: (
        pair[0].question.category_ref.display_order if pair[0].question.category_ref else 0,
        pair[0].question.order,
    ))
    base = calculate_compatibility(user_a, user_b)
    # shared_interests / reasons come from profile data; keep them out of the
    # pair-level analysis so a private preview never leaks profile specifics.
    base.pop('shared_interests', None)
    base.pop('reasons', None)

    # Legacy category list with reflections (kept for the API + existing UI).
    category_scores = core['category_scores']
    categories = []
    for category in QuestionnaireCategory.objects.filter(is_active=True).order_by('display_order', 'name'):
        score = round(sum(category_scores[category.slug]) / len(category_scores[category.slug])) if category.slug in category_scores else 0
        categories.append({
            'slug': category.slug,
            'name': category.name,
            'score': score,
            'reflection': _category_reflection(
                category.name,
                score,
                has_shared_answers=category.slug in category_scores,
            ),
        })

    # Legacy importance groupings.
    importance_items = []
    for response_a, response_b, pair in pairs:
        weight = _importance_weight(response_a, response_b)
        importance_items.append({
            'question': response_a.question.text,
            'category': _category_name(response_a.question),
            'similarity': round(pair['similarity']),
            'importance_weight': weight,
        })
    most_important = [item for item in importance_items if item['importance_weight'] > 1]
    least_important = [item for item in importance_items if item['importance_weight'] < 1]

    def group_score(items):
        return round(sum(item['similarity'] for item in items) / len(items)) if items else None

    result = dict(base)
    result['categories'] = categories
    result['most_important_questions'] = most_important
    result['most_important_similarity'] = group_score(most_important)
    result['least_important_questions'] = least_important
    result['least_important_similarity'] = group_score(least_important)
    # New 'Why You Two Click' story fields.
    result['match'] = {
        'same_wavelength': base['same_wavelength'],
        'balance_each_other': base['balance_each_other'],
        'shared_questions': len(pairs),
    }
    result['shared_dna'] = _shared_dna(pairs)
    result['sparks'] = _sparks(pairs)
    result['mystery_match'] = _mystery_match(pairs)
    result['conversation_starters'] = _conversation_starters(pairs)
    result['guess_game'] = _guess_game(pairs)
    # Canonical (order-independent) pair key so a connection's story is shared
    # whichever student is viewing the page.
    result['pair_fingerprint'] = ''.join(sorted([
        _answers_fingerprint(user_a),
        _answers_fingerprint(user_b),
    ]))
    return result
