"""User management routes for admin"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from app.models.user import User
from app import db
from app.auth_utils import login_required, roles_required
from datetime import datetime
from werkzeug.security import generate_password_hash
import re

admin_users_bp = Blueprint("admin_users", __name__)


def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def get_active_admin_count():
    """Get count of active admin users"""
    return User.query.filter_by(role="admin", is_active=True).count()


def get_current_user():
    """Get current logged-in user"""
    if hasattr(g, 'current_user'):
        return g.current_user
    user_id = session.get("user_id")
    if user_id:
        return User.query.get(user_id)
    return None


@admin_users_bp.route("/admin/users", methods=["GET"])
@login_required
@roles_required("admin")
def users_list():
    """List all users"""
    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin/users.html", users=users)


@admin_users_bp.route("/admin/users/new", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def users_new():
    """Create a new user"""
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()
        role = request.form.get("role", "user")
        is_active = request.form.get("is_active") == "on"
        receive_notifications = request.form.get("receive_notifications") == "on"

        # Validation
        errors = []
        
        if not login_id:
            errors.append("ユーザーIDは必須です。")
        elif User.query.filter_by(login_id=login_id).first():
            errors.append("このユーザーIDは既に存在します。")
        
        if not display_name:
            errors.append("表示名は必須です。")
        
        if not email:
            errors.append("メールアドレスは必須です。")
        elif not is_valid_email(email):
            errors.append("メールアドレスの形式が正しくありません。")
        elif User.query.filter_by(email=email).first():
            errors.append("このメールアドレスは既に使用されています。")
        
        if not password:
            errors.append("パスワードは必須です。")
        elif len(password) < 8:
            errors.append("パスワードは8文字以上である必要があります。")
        
        if password != password_confirm:
            errors.append("パスワードと確認が一致しません。")
        
        if role not in ["admin", "user"]:
            errors.append("権限の値が不正です。")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "admin/user_form.html",
                user=None,
                is_new=True,
                role=role,
                is_active=is_active,
                receive_notifications=receive_notifications,
            )

        # Create user
        user = User(
            login_id=login_id,
            display_name=display_name,
            email=email,
            role=role,
            is_active=is_active,
            receive_notifications=receive_notifications,
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f"ユーザー '{display_name}' を作成しました。", "success")
        return redirect(url_for("admin_users.users_list"))

    # GET: Display empty form with defaults
    return render_template(
        "admin/user_form.html",
        user=None,
        is_new=True,
        role="user",
        is_active=False,
        receive_notifications=True,  # Default: notifications enabled
    )


@admin_users_bp.route("/admin/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def users_edit(user_id):
    """Edit user details"""
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip()
        email = request.form.get("email", "").strip()
        role = request.form.get("role", user.role)
        is_active = request.form.get("is_active") == "on"
        receive_notifications = request.form.get("receive_notifications") == "on"

        # Validation
        errors = []
        
        if not display_name:
            errors.append("表示名は必須です。")
        
        if not email:
            errors.append("メールアドレスは必須です。")
        elif not is_valid_email(email):
            errors.append("メールアドレスの形式が正しくありません。")
        elif User.query.filter_by(email=email).filter(User.id != user_id).first():
            errors.append("このメールアドレスは既に使用されています。")
        
        if role not in ["admin", "user"]:
            errors.append("権限の値が不正です。")

        # Check for admin protection
        current_user = get_current_user()
        
        # Prevent disabling self
        if not is_active and current_user and user.id == current_user.id:
            errors.append("自分自身を無効化することはできません。")
        
        # Prevent removing admin role from self
        if role != "admin" and current_user and user.id == current_user.id:
            errors.append("自分自身の権限を変更することはできません。")
        
        # Protect last active admin
        if user.role == "admin" and not is_active:
            active_admin_count = get_active_admin_count()
            if active_admin_count <= 1:
                errors.append("有効な管理者が1人以上必要です。無効化することはできません。")
        
        if user.role == "admin" and role != "admin":
            active_admin_count = User.query.filter_by(role="admin", is_active=True).filter(User.id != user_id).count()
            if active_admin_count == 0:
                errors.append("有効な管理者が1人以上必要です。権限を変更することはできません。")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "admin/user_form.html",
                user=user,
                is_new=False,
                role=role,
                is_active=is_active,
                receive_notifications=receive_notifications,
            )

        # Update user
        user.display_name = display_name
        user.email = email
        user.role = role
        user.is_active = is_active
        user.receive_notifications = receive_notifications
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f"ユーザー '{display_name}' を更新しました。", "success")
        return redirect(url_for("admin_users.users_list"))

    # GET: Display form with current values
    return render_template(
        "admin/user_form.html",
        user=user,
        is_new=False,
        role=user.role,
        is_active=user.is_active,
        receive_notifications=user.receive_notifications,
    )


@admin_users_bp.route("/admin/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def users_reset_password(user_id):
    """Reset user password"""
    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        password = request.form.get("password", "").strip()
        password_confirm = request.form.get("password_confirm", "").strip()

        # Validation
        errors = []
        
        if not password:
            errors.append("新しいパスワードは必須です。")
        elif len(password) < 8:
            errors.append("パスワードは8文字以上である必要があります。")
        
        if password != password_confirm:
            errors.append("パスワードと確認が一致しません。")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("admin/user_password_reset.html", user=user)

        # Update password
        user.set_password(password)
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f"ユーザー '{user.display_name}' のパスワードをリセットしました。", "success")
        return redirect(url_for("admin_users.users_list"))

    return render_template("admin/user_password_reset.html", user=user)


@admin_users_bp.route("/admin/users/<int:user_id>/toggle-active", methods=["POST"])
@login_required
@roles_required("admin")
def users_toggle_active(user_id):
    """Toggle user active status"""
    current_user = get_current_user()
    user = User.query.get_or_404(user_id)
    
    # Prevent disabling self
    if current_user and user.id == current_user.id:
        flash("自分自身を無効化することはできません。", "danger")
        return redirect(url_for("admin_users.users_list"))
    
    # Protect last active admin
    if user.role == "admin" and user.is_active:
        active_admin_count = get_active_admin_count()
        if active_admin_count <= 1:
            flash("有効な管理者が1人以上必要です。無効化することはできません。", "danger")
            return redirect(url_for("admin_users.users_list"))
    
    # Toggle
    user.is_active = not user.is_active
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = "有効化" if user.is_active else "無効化"
    flash(f"ユーザー '{user.display_name}' を{status}しました。", "success")
    return redirect(url_for("admin_users.users_list"))
