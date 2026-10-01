from rest_framework import serializers

from .models import Question, QuestionOption, QuestionnaireCategory, QuestionResponse


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('id', 'option_text', 'option_value', 'display_order', 'compatibility_value')


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, read_only=True)
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            'id', 'category', 'category_name', 'text', 'question_type',
            'help_text', 'order', 'is_required', 'options',
        )

    def get_category_name(self, obj):
        return obj.category_ref.name if obj.category_ref else obj.category


class CategorySerializer(serializers.ModelSerializer):
    question_count = serializers.IntegerField(read_only=True)
    answered_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = QuestionnaireCategory
        fields = ('id', 'name', 'slug', 'description', 'icon', 'display_order', 'question_count', 'answered_count')


class ResponseSerializer(serializers.ModelSerializer):
    value = serializers.CharField(required=False, allow_blank=True, default='')
    other_text = serializers.CharField(required=False, allow_blank=True, max_length=500, default='')
    importance = serializers.ChoiceField(choices=QuestionResponse.Importance.choices)
    selected_option_ids = serializers.PrimaryKeyRelatedField(
        source='selected_options', many=True, queryset=QuestionOption.objects.all(),
        required=False,
    )

    class Meta:
        model = QuestionResponse
        fields = ('id', 'question', 'value', 'other_text', 'importance', 'selected_option_ids', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate(self, attrs):
        question = attrs.get('question', self.instance.question if self.instance else None)
        selected = attrs.get('selected_options', [])
        other_text = attrs.get('other_text', '').strip()
        attrs['other_text'] = other_text
        value = attrs.get('value', '')
        if question and question.question_type == 'SINGLE_CHOICE':
            if other_text and selected:
                raise serializers.ValidationError({
                    'selected_option_ids': 'Choose either one option or Other, not both.',
                })
            if not other_text and len(selected) != 1:
                raise serializers.ValidationError({
                    'selected_option_ids': 'Select one option or provide an Other answer.',
                })
        if question and question.question_type == 'YES_NO' and len(selected) != 1:
            raise serializers.ValidationError({'selected_option_ids': 'Select exactly one option.'})
        if question and question.question_type == 'MULTIPLE_CHOICE' and not selected and not other_text:
            raise serializers.ValidationError({
                'selected_option_ids': 'Select at least one option or provide an Other answer.',
            })
        if question and question.question_type not in ('SINGLE_CHOICE', 'MULTIPLE_CHOICE') and other_text:
            raise serializers.ValidationError({
                'other_text': 'Other answers are only supported for choice questions.',
            })
        if question and question.question_type == 'SCALE':
            try:
                score = int(value)
            except (TypeError, ValueError):
                raise serializers.ValidationError({'value': 'Scale answers must be numeric.'})
            if score < 1 or score > 5:
                raise serializers.ValidationError({'value': 'Scale answers must be between 1 and 5.'})
        if question and selected and any(option.question_id != question.id for option in selected):
            raise serializers.ValidationError({'selected_option_ids': 'Options must belong to the selected question.'})
        return attrs

    def create(self, validated_data):
        selected = validated_data.pop('selected_options', [])
        response, _ = QuestionResponse.objects.update_or_create(
            user=self.context['request'].user,
            question=validated_data['question'],
            defaults={
                'value': validated_data.get('value', ''),
                'other_text': validated_data.get('other_text', ''),
                'importance': validated_data['importance'],
            },
        )
        response.selected_options.set(selected)
        return response

    def update(self, instance, validated_data):
        selected = validated_data.pop('selected_options', None)
        instance.value = validated_data.get('value', instance.value)
        instance.other_text = validated_data.get('other_text', instance.other_text)
        instance.importance = validated_data.get('importance', instance.importance)
        instance.save(update_fields=('value', 'other_text', 'importance'))
        if selected is not None:
            instance.selected_options.set(selected)
        return instance
