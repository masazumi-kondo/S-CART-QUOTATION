from functools import wraps
from flask import g, redirect, url_for, request, abort, current_app

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, "current_user", None):
            next_url = request.full_path
            return redirect(url_for("auth.login", next=next_url))
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                next_url = request.full_path
                return redirect(url_for("auth.login", next=next_url))
            if user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Permission helper functions
def is_admin_user(user):
    """Check if user is an administrator"""
    return user and user.is_authenticated and user.role == "admin"

def can_approve_user(user):
    """Check if user can approve (admin or approver)"""
    return user and user.is_authenticated and user.role in ["admin", "approver"]

def approval_required(f):
    """Decorator for routes requiring approval permissions (admin or approver)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = getattr(g, "current_user", None)
        if not user:
            next_url = request.full_path
            return redirect(url_for("auth.login", next=next_url))
        if user.role not in ["admin", "approver"]:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
