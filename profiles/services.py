from profiles.models import Profile
from connections.models import Connection
from django.db.models import Q


def can_view_full_profile(viewer, profile_owner):
    """Return whether a viewer may receive another user's private profile data."""
    if not viewer or not getattr(viewer, 'is_authenticated', False):
        return False
    if viewer.pk == profile_owner.pk:
        return True
    return Connection.objects.filter(
        Q(requester=viewer, recipient=profile_owner) |
        Q(requester=profile_owner, recipient=viewer),
        status__in=('ACCEPTED', 'CONNECTED'),
    ).exists()


def get_profile_strength(user):
    """Return server-calculated completion details for a user's profile."""
    profile = getattr(user, 'profile', None)
    if not profile:
        return {
            'profile_strength': 0,
            'completed_fields': 0,
            'total_fields': 10,
            'missing_fields': [
                'Age', 'City', 'Gender', 'Languages', 'Profile Photo',
                'Bio', 'University', 'Major', 'Year', 'Interests',
            ],
        }

    fields = [
        ('Age', profile.age),
        ('City', profile.city),
        ('Gender', profile.gender),
        ('Languages', profile.languages),
        ('Profile Photo', profile.photo),
        ('Bio', profile.bio),
        ('University', profile.university),
        ('Major', profile.major),
        ('Year', profile.year),
        ('Interests', profile.interests),
    ]
    completed = [label for label, value in fields if value and str(value).strip()]
    missing = [label for label, value in fields if not value or not str(value).strip()]
    return {
        'profile_strength': int(round(len(completed) / len(fields) * 100)),
        'completed_fields': len(completed),
        'total_fields': len(fields),
        'missing_fields': missing,
    }


def get_profile_completion(user):
    """Calculate profile completeness percentage from Profile fields."""
    return get_profile_strength(user)['profile_strength']
