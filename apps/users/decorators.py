from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.users.permissions import user_has_module_permission


def require_permission(module, action='read'):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if not user_has_module_permission(request.user, module, action):
                return render(request, '403.html', status=403)
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def require_admin(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_admin_user:
            return render(request, '403.html', status=403)
        return view_func(request, *args, **kwargs)

    return _wrapped
