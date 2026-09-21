from collections import OrderedDict

from django.db.models import Count

from .models import Question, QuestionResponse, QuestionnaireCategory


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


def seed_questionnaire_data():
    categories = [
        ('Values', 'values', 'Principles and priorities when working with others.', 'heart'),
        ('Learning Style', 'learning-style', 'How you learn and solve problems.', 'book-open'),
        ('Communication', 'communication', 'How you collaborate and communicate.', 'message-circle'),
        ('Career Goals', 'career-goals', 'Your professional direction and motivation.', 'target'),
        ('Lifestyle', 'lifestyle', 'Study habits and working preferences.', 'clock'),
        ('Interests', 'interests', 'Technical, academic, and extracurricular interests.', 'sparkles'),
    ]
    created = 0
    for order, (name, slug, description, icon) in enumerate(categories):
        category, _ = QuestionnaireCategory.objects.update_or_create(
            slug=slug,
            defaults={'name': name, 'description': description, 'icon': icon, 'display_order': order},
        )
        questions = {
            'values': [
                ('What matters most when working with a teammate?', 'SINGLE_CHOICE', ['Reliability', 'Creativity', 'Communication', 'Responsibility', 'Flexibility']),
                ('How do you prefer to handle disagreements?', 'SINGLE_CHOICE', ['Discuss them directly', 'Take time to reflect', 'Ask a neutral teammate', 'Look for a compromise']),
            ],
            'learning-style': [
                ('How do you prefer to learn a new technology?', 'SINGLE_CHOICE', ['Video tutorials', 'Documentation', 'Hands-on projects', 'Group discussion', 'Mentoring']),
                ('What helps you understand a difficult concept?', 'SINGLE_CHOICE', ['Examples', 'Visual diagrams', 'Practice exercises', 'A detailed explanation']),
            ],
            'communication': [
                ('How often do you prefer to communicate during a team project?', 'SINGLE_CHOICE', ['Only when necessary', 'Once a day', 'Several times a day', 'Frequent collaboration']),
                ('Which communication style works best for you?', 'SINGLE_CHOICE', ['Concise messages', 'Detailed written notes', 'Voice or video calls', 'A mix depending on the situation']),
            ],
            'career-goals': [
                ('What best describes your current career goal?', 'SINGLE_CHOICE', ['Software Engineering', 'Data Engineering', 'AI / ML', 'Cloud / DevOps', 'Research', 'Entrepreneurship']),
                ('What motivates you most in a project?', 'SINGLE_CHOICE', ['Building useful products', 'Learning new skills', 'Solving challenging problems', 'Making a social impact']),
            ],
            'lifestyle': [
                ('When do you prefer studying?', 'SINGLE_CHOICE', ['Early morning', 'Morning', 'Afternoon', 'Evening', 'Late night']),
                ('What is your ideal study session?', 'SINGLE_CHOICE', ['Short focused blocks', 'One long session', 'Flexible sessions', 'Scheduled group work']),
            ],
            'interests': [
                ('Which activities are you most interested in?', 'MULTIPLE_CHOICE', ['AI', 'Cloud', 'Coding', 'Hackathons', 'Startups', 'Open Source', 'Research', 'Sports', 'Design', 'Photography']),
                ('Which projects would you enjoy collaborating on?', 'MULTIPLE_CHOICE', ['Mobile apps', 'Web platforms', 'Data visualizations', 'Robotics', 'Community projects', 'Creative tools']),
            ],
        }[slug]
        for question_order, (text, question_type, options) in enumerate(questions):
            question, _ = Question.objects.update_or_create(
                category=slug, order=question_order,
                defaults={'category_ref': category, 'text': text, 'question_type': question_type, 'is_active': True},
            )
            for option_order, option_text in enumerate(options):
                from .models import QuestionOption
                QuestionOption.objects.update_or_create(
                    question=question, option_value=option_text.lower().replace(' ', '-'),
                    defaults={'option_text': option_text, 'display_order': option_order},
                )
            created += 1
    return created
