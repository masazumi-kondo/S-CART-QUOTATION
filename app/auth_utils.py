from functools import wraps
from flask import g, redirect, url_for, request, abort

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
