from profiles.models import Profile


def get_profile_completion(user):
    """Calculate profile completeness percentage from Profile fields."""
    if not user or not hasattr(user, 'profile'):
        return 0
    profile = user.profile
    fields = [
        profile.age,
        profile.city,
        profile.gender,
        profile.languages,
        profile.university,
        profile.major,
        profile.year,
        profile.bio,
        profile.interests,
    ]
    filled = sum(1 for f in fields if f and str(f).strip())
    # include photo presence as bonus
    if profile.photo:
        filled += 1
    total = len(fields) + 1  # + photo
    return int(round((filled / total) * 100))
