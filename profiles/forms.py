from django import forms

from .models import Profile


class ProfileSetupForm(forms.ModelForm):
    display_name = forms.CharField(
        max_length=150,
        label='Display name',
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'How should others see your name?',
            'autocomplete': 'name',
        }),
    )
    age = forms.IntegerField(
        required=False,
        min_value=16,
        max_value=100,
        widget=forms.NumberInput(attrs={'placeholder': 'Age'}),
    )
    gender = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Select gender'),
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Non-Binary', 'Non-Binary'),
            ('Prefer Not To Say', 'Prefer Not To Say'),
        ],
    )
    languages = forms.MultipleChoiceField(
        required=False,
        choices=[
            ('English', 'English'),
            ('Hindi', 'Hindi'),
            ('Telugu', 'Telugu'),
            ('Tamil', 'Tamil'),
            ('Kannada', 'Kannada'),
            ('Malayalam', 'Malayalam'),
        ],
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Profile
        fields = ('age', 'city', 'gender', 'university', 'major', 'year', 'bio', 'photo')
        widgets = {
            'city': forms.TextInput(attrs={'placeholder': 'Your city'}),
            'university': forms.TextInput(attrs={'placeholder': 'Your university'}),
            'major': forms.TextInput(attrs={'placeholder': 'e.g. Computer Science'}),
            'year': forms.Select(choices=[
                ('', 'Select year'),
                ('1st Year', '1st Year'),
                ('2nd Year', '2nd Year'),
                ('3rd Year', '3rd Year'),
                ('4th Year', '4th Year'),
                ('Graduate', 'Graduate'),
            ]),
            'bio': forms.Textarea(attrs={
                'placeholder': 'Tell students a little about yourself...',
                'maxlength': 500,
                'rows': 4,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['display_name'].initial = user.get_full_name() if user else ''
        self.fields['languages'].initial = [
            language.strip()
            for language in (self.instance.languages or '').split(',')
            if language.strip()
        ]

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.languages = ', '.join(self.cleaned_data.get('languages', []))
        profile.interests = profile.interests.strip()
        if commit:
            profile.save()
            display_name = self.cleaned_data['display_name'].strip()
            name_parts = display_name.split(maxsplit=1)
            self.user.first_name = name_parts[0]
            self.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            self.user.save(update_fields=['first_name', 'last_name', 'updated_at'])
        return profile
