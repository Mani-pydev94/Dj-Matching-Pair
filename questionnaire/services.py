import json
from pathlib import Path

from django.db import transaction
from django.db.models import Count

from profiles.models import Profile

from .models import Question, QuestionOption, QuestionResponse, QuestionnaireCategory


def questionnaire_progress(user):
    questions = Question.objects.filter(is_active=True, is_required=True)
    total = questions.count()
    answered = QuestionResponse.objects.filter(user=user, question__in=questions).count()
    categories = QuestionnaireCategory.objects.filter(is_active=True).annotate(
        question_count=Count('questions', filter=None),
    )
    completed_categories = 0
    for category in categories:
        category_questions = questions.filter(category_ref=category)
        if category_questions.exists() and not category_questions.exclude(
            id__in=QuestionResponse.objects.filter(user=user).values('question_id')
        ).exists():
            completed_categories += 1
    next_question = questions.exclude(
        id__in=QuestionResponse.objects.filter(user=user).values('question_id')
    ).first()
    return {
        'total_questions': total,
        'answered_questions': answered,
        'completion_percentage': int(round(answered / total * 100)) if total else 0,
        'completed_categories': completed_categories,
        'remaining_categories': max(categories.count() - completed_categories, 0),
        'is_complete': total > 0 and answered >= total,
        'next_question_id': next_question.id if next_question else None,
    }


@transaction.atomic
def seed_questionnaire_data():
    data_path = Path(__file__).with_name('questionnaire_data.json')
    with data_path.open(encoding='utf-8') as data_file:
        categories_data = json.load(data_file)

    Question.objects.all().delete()
    QuestionnaireCategory.objects.all().delete()
    Profile.objects.filter(questionnaire_completed=True).update(questionnaire_completed=False)

    question_count = 0
    for category_order, category_data in enumerate(categories_data):
        category = QuestionnaireCategory.objects.create(
            name=category_data['name'],
            slug=category_data['slug'],
            description=category_data['description'],
            icon=category_data['icon'],
            display_order=category_order,
        )
        for question_order, question_data in enumerate(category_data['questions']):
            question = Question.objects.create(
                question_key=f"{category.slug}-{question_order + 1:03d}",
                category=category.slug,
                category_ref=category,
                text=question_data['text'],
                question_type='SINGLE_CHOICE',
                order=question_order,
                weight=1.0,
                is_required=True,
                is_active=True,
            )
            QuestionOption.objects.bulk_create([
                QuestionOption(
                    question=question,
                    option_text=option_text,
                    option_value=f'answer-{option_order + 1}',
                    display_order=option_order,
                )
                for option_order, option_text in enumerate(question_data['options'])
            ])
            question_count += 1

    return question_count
