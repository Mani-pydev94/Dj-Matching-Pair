from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SignupForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=200, required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your full name',
            'autocomplete': 'name',
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your college email',
            'autocomplete': 'email',
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })
    )
    terms = forms.BooleanField(
        required=True,
        label=_('I agree to the Terms of Service and Privacy Policy.')
    )

    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('An account with this email already exists.'))
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError(_('Passwords do not match.'))
        if not cleaned.get('terms'):
            raise ValidationError(_('You must agree to the Terms of Service and Privacy Policy.'))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = user.email  # keep Django happy for AbstractUser internals
        user.email = self.cleaned_data['email'].lower().strip()
        user.set_password(self.cleaned_data['password1'])
        # Split full_name
        full = self.cleaned_data.get('full_name', '').strip()
        parts = full.split()
        user.first_name = parts[0] if len(parts) > 0 else ''
        user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        if commit:
            user.save()
            # Auto-create profile
            from profiles.models import Profile
            Profile.objects.get_or_create(user=user)
        return user


class LoginForm(forms.Form):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
        })
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )
