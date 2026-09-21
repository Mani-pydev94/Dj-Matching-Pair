from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

from communities.models import Community
from events.models import Event
from events.forms import EventAdminForm
from questionnaire.models import Question, QuestionOption, QuestionnaireCategory
from profiles.models import Profile


User = get_user_model()


class UserAdminForm(forms.ModelForm):
    university = forms.CharField(required=False)
    city = forms.CharField(required=False)
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(), required=False, widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active', 'is_staff', 'groups')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            profile = getattr(self.instance, 'profile', None)
            self.fields['university'].initial = profile.university if profile else ''
            self.fields['city'].initial = profile.city if profile else ''

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.university = self.cleaned_data['university']
            profile.city = self.cleaned_data['city']
            profile.save(update_fields=('university', 'city', 'updated_at'))
            user.groups.set(self.cleaned_data['groups'])
        return user


class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ('name', 'description', 'category')


class CategoryForm(forms.ModelForm):
    class Meta:
        model = QuestionnaireCategory
        fields = ('name', 'slug', 'description', 'icon', 'display_order', 'is_active')


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = (
            'question_key', 'category_ref', 'text', 'question_type', 'help_text', 'order',
            'weight', 'is_required', 'is_active',
        )

    def save(self, commit=True):
        question = super().save(commit=False)
        if question.category_ref:
            question.category = question.category_ref.name
        if commit:
            question.save()
        return question


class OptionForm(forms.ModelForm):
    class Meta:
        model = QuestionOption
        fields = ('option_text', 'option_value', 'compatibility_value', 'display_order', 'is_active')
        labels = {
            'option_text': 'Text',
            'option_value': 'Value',
            'compatibility_value': 'Score',
            'display_order': 'Order',
            'is_active': 'Active',
        }

    def clean_option_value(self):
        return self.cleaned_data['option_value'].strip()


class BaseOptionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        values = set()
        active_count = 0
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            value = form.cleaned_data.get('option_value')
            if value and value in values:
                raise forms.ValidationError('Option value must be unique for this question.')
            if value:
                values.add(value)
            if form.cleaned_data.get('is_active') and value:
                active_count += 1
        question_type = self.instance.question_type if self.instance else None
        if self.instance and self.instance.is_active and question_type in ('SINGLE_CHOICE', 'MULTIPLE_CHOICE') and active_count < 2:
            raise forms.ValidationError('Active choice questions should have at least 2 active answer options.')


OptionFormSet = inlineformset_factory(
    Question,
    QuestionOption,
    form=OptionForm,
    formset=BaseOptionFormSet,
    extra=1,
    can_delete=True,
)


class GroupForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'codename',
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Group
        fields = ('name', 'permissions')
