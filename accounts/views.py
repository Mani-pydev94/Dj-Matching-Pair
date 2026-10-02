import secrets
import smtplib
import string
import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import BadHeaderError, send_mail
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_POST

from .forms import SignupForm, LoginForm, SignupOTPForm
from .models import SignupOTP

User = get_user_model()
logger = logging.getLogger(__name__)
OTP_SESSION_KEY = 'pending_signup_user_id'
OTP_LENGTH = 6
OTP_TTL = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 5
OTP_ALPHABET = string.ascii_uppercase + string.digits


class EmailDeliveryError(Exception):
    pass


EMAIL_DELIVERY_ERRORS = (
    EmailDeliveryError,
    BadHeaderError,
    ImproperlyConfigured,
    OSError,
    smtplib.SMTPException,
)


class OTPResendCooldown(Exception):
    def __init__(self, seconds):
        self.seconds = seconds


def _otp_digest(user, code):
    return salted_hmac(
        'accounts.SignupOTP',
        f'{user.pk}:{code}',
        algorithm='sha256',
    ).hexdigest()


def _issue_signup_otp(user, otp=None):
    now = timezone.now()
    if otp and now - otp.last_sent_at < OTP_RESEND_COOLDOWN:
        remaining = int((OTP_RESEND_COOLDOWN - (now - otp.last_sent_at)).total_seconds())
        raise OTPResendCooldown(max(remaining, 1))

    characters = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        *(secrets.choice(OTP_ALPHABET) for _ in range(OTP_LENGTH - 2)),
    ]
    secrets.SystemRandom().shuffle(characters)
    code = ''.join(characters)
    if otp is None:
        otp = SignupOTP(user=user)
    otp.token_digest = _otp_digest(user, code)
    otp.expires_at = now + OTP_TTL
    otp.last_sent_at = now
    otp.attempts = 0
    otp.save()

    sent = send_mail(
        subject='Your Campus Connect verification code',
        message=(
            f'Your email verification code is {code}.\n\n'
            'Enter this 6-character code to verify your email address. '
            'The code expires in 10 minutes and can only be used once.'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    if sent != 1:
        raise EmailDeliveryError('The email backend did not send the verification email.')


def _pending_signup_user(request):
    user_id = request.session.get(OTP_SESSION_KEY)
    if not user_id:
        return None
    return User.objects.filter(
        pk=user_id,
        is_active=False,
        is_verified=False,
    ).first()


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    user.is_active = False
                    user.is_verified = False
                    user.save()
                    from profiles.models import Profile
                    Profile.objects.get_or_create(user=user)
                    _issue_signup_otp(user)
            except EMAIL_DELIVERY_ERRORS as exc:
                logger.error('Signup verification email failed (%s).', type(exc).__name__)
                form.add_error(None, 'We could not send your verification email. Please try again.')
            else:
                request.session[OTP_SESSION_KEY] = str(user.pk)
                messages.info(request, 'We sent a verification code to your email address.')
                return redirect('verify_signup_email')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


def verify_signup_email(request):
    if request.user.is_authenticated:
        return redirect('home')
    user = _pending_signup_user(request)
    if user is None:
        request.session.pop(OTP_SESSION_KEY, None)
        messages.info(request, 'Create an account to start email verification.')
        return redirect('signup')

    otp = SignupOTP.objects.filter(user=user).first()
    if otp is None:
        request.session.pop(OTP_SESSION_KEY, None)
        messages.error(request, 'The verification request is no longer available. Please sign up again.')
        return redirect('signup')

    form = SignupOTPForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            otp = SignupOTP.objects.select_for_update().filter(user=user).first()
            if otp is None:
                form.add_error(None, 'The verification request is no longer available. Please sign up again.')
            elif otp.attempts >= OTP_MAX_ATTEMPTS:
                form.add_error(None, 'Too many incorrect attempts. Request a new code to continue.')
            elif otp.expires_at <= timezone.now():
                form.add_error(None, 'This code has expired. Request a new code to continue.')
            elif secrets.compare_digest(otp.token_digest, _otp_digest(user, form.cleaned_data['code'])):
                user.is_verified = True
                user.is_active = True
                user.save(update_fields=('is_verified', 'is_active', 'updated_at'))
                otp.delete()
                request.session.pop(OTP_SESSION_KEY, None)
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Your email is verified. Welcome to Campus Connect!')
                return redirect('profiles:profile_setup')
            else:
                otp.attempts += 1
                otp.save(update_fields=('attempts',))
                remaining = OTP_MAX_ATTEMPTS - otp.attempts
                if remaining:
                    form.add_error('code', f'That code is incorrect. You have {remaining} attempts remaining.')
                else:
                    form.add_error(None, 'Too many incorrect attempts. Request a new code to continue.')

    return render(request, 'accounts/verify_email.html', {
        'form': form,
        'email': user.email,
    })


@require_POST
def resend_signup_otp(request):
    if request.user.is_authenticated:
        return redirect('home')
    user = _pending_signup_user(request)
    if user is None:
        request.session.pop(OTP_SESSION_KEY, None)
        messages.error(request, 'Your verification request is no longer available. Please sign up again.')
        return redirect('signup')

    try:
        with transaction.atomic():
            otp = SignupOTP.objects.select_for_update().filter(user=user).first()
            if otp is None:
                request.session.pop(OTP_SESSION_KEY, None)
                messages.error(request, 'Your verification request is no longer available. Please sign up again.')
                return redirect('signup')
            _issue_signup_otp(user, otp)
    except OTPResendCooldown as exc:
        messages.warning(request, f'Please wait {exc.seconds} seconds before requesting another code.')
    except EMAIL_DELIVERY_ERRORS as exc:
        logger.error('Resending signup verification email failed (%s).', type(exc).__name__)
        messages.error(request, 'We could not send a new verification email. Please try again.')
    else:
        messages.success(request, 'A new verification code was sent to your email.')
    return redirect('verify_signup_email')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user, backend="django.contrib.auth.backends.ModelBackend")
                # messages.success(request, 'Welcome back!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    # messages.success(request, 'Logged out successfully.')
    return redirect('login')
