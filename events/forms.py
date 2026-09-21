from django import forms
from django.core.validators import RegexValidator

from .models import EventRegistration
from .models import Event


class EventAdminForm(forms.ModelForm):
    color = forms.CharField(
        label='Event color',
        max_length=7,
        validators=[RegexValidator(r'^#[0-9A-Fa-f]{6}$', 'Enter a valid hexadecimal color such as #7C4DFF.')],
        widget=forms.TextInput(attrs={'type': 'color', 'style': 'height:42px;padding:4px;max-width:90px;'}),
    )

    class Meta:
        model = Event
        fields = ('title', 'description', 'start', 'location', 'color')
        widgets = {'start': forms.DateTimeInput(attrs={'type': 'datetime-local'})}


class EventRegistrationForm(forms.ModelForm):
    class Meta:
        model = EventRegistration
        fields = ('name', 'email', 'phone_number')
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your full name', 'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com', 'autocomplete': 'email'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Your phone number', 'autocomplete': 'tel'}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip()
        digits = ''.join(character for character in phone if character.isdigit())
        if len(digits) < 7:
            raise forms.ValidationError('Enter a valid phone number.')
        return phone
