from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Profile

User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='user.get_full_name', read_only=True)
    languages = serializers.SerializerMethodField()
    profile_photo = serializers.ImageField(source='photo', read_only=True)

    class Meta:
        model = Profile
        fields = (
            'id', 'display_name', 'profile_photo', 'age', 'city', 'gender',
            'languages', 'bio', 'university', 'major', 'year', 'interests',
            'is_public', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'display_name', 'profile_photo', 'is_public',
            'created_at', 'updated_at',
        )

    def get_languages(self, obj):
        return [value.strip() for value in obj.languages.split(',') if value.strip()]

    def validate_gender(self, value):
        allowed = {'Male', 'Female', 'Non-Binary', 'Prefer Not To Say', ''}
        if value not in allowed:
            raise serializers.ValidationError('Select a supported gender.')
        return value

    def update(self, instance, validated_data):
        display_name = self.initial_data.get('display_name')
        if display_name is not None:
            display_name = str(display_name).strip()
            if not display_name:
                raise serializers.ValidationError({'display_name': 'Display name cannot be empty.'})
            parts = display_name.split(maxsplit=1)
            instance.user.first_name = parts[0]
            instance.user.last_name = parts[1] if len(parts) > 1 else ''
            instance.user.save(update_fields=('first_name', 'last_name', 'updated_at'))
        languages = self.initial_data.get('languages')
        if languages is not None:
            if not isinstance(languages, list):
                raise serializers.ValidationError({'languages': 'Languages must be a list.'})
            instance.languages = ', '.join(str(item).strip() for item in languages if str(item).strip())
        return super().update(instance, validated_data)


class PublicStudentProfileSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='user.get_full_name', read_only=True)
    profile_photo = serializers.ImageField(source='photo', read_only=True)
    languages = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'id', 'display_name', 'profile_photo', 'age', 'city', 'university',
            'major', 'year', 'languages', 'bio', 'interests',
        )

    def get_languages(self, obj):
        return [value.strip() for value in obj.languages.split(',') if value.strip()]


class ProfilePreviewSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'display_name')


class ProfileStatsSerializer(serializers.Serializer):
    communities_count = serializers.IntegerField()
    chats_count = serializers.IntegerField()
    events_count = serializers.IntegerField()
    answers_count = serializers.IntegerField()


class ProfileStrengthSerializer(serializers.Serializer):
    profile_strength = serializers.IntegerField()
    completed_fields = serializers.IntegerField()
    total_fields = serializers.IntegerField()
    missing_fields = serializers.ListField(child=serializers.CharField())
