
from functools import wraps
from flask import session, redirect, url_for, g, abort

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        if not session.get("user_id"):
            next_url = request.full_path
            if next_url.endswith('?'):
                next_url = next_url[:-1]
            return redirect(url_for("auth.login", next=next_url))
        return f(*args, **kwargs)
    return decorated_function


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            if not session.get("user_id"):
                next_url = request.full_path
                if next_url.endswith('?'):
                    next_url = next_url[:-1]
                return redirect(url_for("auth.login", next=next_url))
            user = getattr(g, "current_user", None)
            if not user or user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
