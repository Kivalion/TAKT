from functools import wraps
from flask import g, abort
from flask_login import current_user


def module_required(module_name):
    """Decorator: ensures the module is enabled for g.tenant."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not g.tenant:
                abort(403)
            if not g.tenant.is_module_enabled(module_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    """Decorator: ensures current user is a tenant admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def super_admin_required(f):
    """Decorator: ensures current user is a SuperAdminUser."""
    from takt.app.models.public import SuperAdminUser
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if not isinstance(current_user._get_current_object(), SuperAdminUser):
            abort(403)
        return f(*args, **kwargs)
    return decorated
