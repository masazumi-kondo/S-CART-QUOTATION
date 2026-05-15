
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
            from flask import request, current_app
            import sys
            import json
            from datetime import datetime
            
            timestamp = datetime.now().isoformat()
            
            if not session.get("user_id"):
                next_url = request.full_path
                if next_url.endswith('?'):
                    next_url = next_url[:-1]
                return redirect(url_for("auth.login", next=next_url))
            user = getattr(g, "current_user", None)
            
            # Detailed debug output
            debug_info = {
                "timestamp": timestamp,
                "route": f.__name__,
                "session_user_id": session.get("user_id"),
                "user_object": str(user),
                "user_is_none": user is None,
                "required_roles": roles,
            }
            if user:
                debug_info["user_login_id"] = user.login_id
                debug_info["user_role_value"] = user.role
                debug_info["user_role_type"] = str(type(user.role))
                debug_info["user_role_in_required"] = user.role in roles
                debug_info["check_result"] = user.role in roles
            else:
                debug_info["check_result"] = False
            
            # Write to file
            try:
                with open("decorators_debug.log", "a") as logfile:
                    logfile.write(f"[ROLES_DEBUG] {json.dumps(debug_info)}\n")
            except:
                pass
            
            # Also print to stderr
            print(f"[ROLES_DEBUG] {json.dumps(debug_info)}", file=sys.stderr)
            sys.stderr.flush()
            
            if not user or user.role not in roles:
                print(f"[ROLES_DENY] route={f.__name__}, user={user.login_id if user else None}, reason={'NO_USER' if not user else f'role={user.role} not in {roles}'}", file=sys.stderr)
                sys.stderr.flush()
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
