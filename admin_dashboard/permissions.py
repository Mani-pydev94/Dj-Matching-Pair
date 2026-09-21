from functools import wraps

from django.core.exceptions import PermissionDenied


def dashboard_access(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def can_manage(request, permission):
    return request.user.is_superuser or request.user.has_perm(permission)
