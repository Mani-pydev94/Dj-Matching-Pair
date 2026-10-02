from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.utils.text import slugify

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
    order = forms.IntegerField(required=False, min_value=0, label='Order (leave blank to assign)')

    class Meta:
        model = Question
        fields = (
            'question_key', 'category_ref', 'text', 'question_type', 'help_text',
            'image', 'image_alt_text', 'order',
            'weight', 'is_required', 'is_active',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['question_key'].label = 'Question key (leave blank to generate)'
        if not self.instance.pk:
            self.fields['order'].initial = None

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('image') and cleaned_data.get('question_type') != 'SINGLE_CHOICE':
            self.add_error('question_type', 'Image questions must use single-choice answers.')
        return cleaned_data

    def save(self, commit=True):
        question = super().save(commit=False)
        if question.category_ref:
            question.category = question.category_ref.name
        if commit:
            question.save()
        return question


class OptionForm(forms.ModelForm):
    option_value = forms.CharField(required=False, label='Value (leave blank to generate)')
    display_order = forms.IntegerField(
        required=False,
        min_value=0,
        label='Order (leave blank to assign)',
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['display_order'].initial = None


class BaseOptionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        forms_to_save = []
        used_values = set()
        next_order = max(
            (
                form.cleaned_data['display_order']
                for form in self.forms
                if form.cleaned_data
                and not form.cleaned_data.get('DELETE')
                and form.cleaned_data.get('display_order') is not None
            ),
            default=0,
        ) + 1

        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            option_text = form.cleaned_data.get('option_text', '').strip()
            if not option_text:
                continue
            if form.cleaned_data.get('display_order') is None:
                form.cleaned_data['display_order'] = next_order
                form.instance.display_order = next_order
                next_order += 1
            value = form.cleaned_data.get('option_value', '').strip()
            if value:
                used_values.add(value)
            forms_to_save.append(form)

        generated_values = set()
        for form in forms_to_save:
            if form.cleaned_data.get('option_value'):
                continue
            base_value = slugify(form.cleaned_data['option_text']) or (
                f"option-{form.cleaned_data['display_order']}"
            )
            value = base_value
            suffix = 2
            while value in used_values or value in generated_values:
                value = f'{base_value}-{suffix}'
                suffix += 1
            form.cleaned_data['option_value'] = value
            form.instance.option_value = value
            generated_values.add(value)

        values = set()
        active_count = 0
        for form in forms_to_save:
            value = form.cleaned_data['option_value']
            if value and value in values:
                raise forms.ValidationError('Option value must be unique for this question.')
            if value:
                values.add(value)
            if form.cleaned_data.get('is_active'):
                active_count += 1
        question_type = self.instance.question_type if self.instance else None
        if self.instance and self.instance.is_active and question_type in ('SINGLE_CHOICE', 'MULTIPLE_CHOICE') and active_count < 2:
            raise forms.ValidationError('Active choice questions should have at least 2 active answer options.')
        if self.instance and self.instance.image and active_count != 4:
            raise forms.ValidationError('Image questions must have exactly 4 active answer options.')


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
