
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from datetime import datetime
from app.decorators import login_required, roles_required
from app import db
from app.models.user import User
from werkzeug.security import generate_password_hash

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if session.get("user_id"):
        return redirect(url_for("main.index"))
    next_url = request.values.get("next")
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(login_id=login_id).first()
        result = None
        user_id_val = None
        from werkzeug.security import check_password_hash
        if (not user) or (not check_password_hash(user.password_hash, password)):
            flash("ユーザーIDまたはパスワードが違います。", "danger")
            result = "fail"
            _insert_login_log(login_id, user_id_val, result)
            return render_template("login.html", next=next_url)

        if not user.is_active:
            flash("このアカウントは承認待ちです。管理者に連絡してください。", "warning")
            result = "inactive"
            user_id_val = user.id
            _insert_login_log(login_id, user_id_val, result)
            return render_template("login.html", next=next_url)

        # OKならログイン処理へ
        session["user_id"] = user.id
        flash("ログインしました。", "success")
        result = "success"
        user_id_val = user.id
        if getattr(user, "must_change_password", 0) == 1:
            _insert_login_log(login_id, user_id_val, "success")
            return redirect(url_for("auth.force_change_password"))
        # オープンリダイレクト対策: next_urlが / で始まる場合のみ許可
        if next_url and next_url.startswith("/") and not next_url.startswith("//") and not next_url.startswith("/\\"):
            _insert_login_log(login_id, user_id_val, result)
            return redirect(next_url)
        else:
            _insert_login_log(login_id, user_id_val, result)
            return redirect(url_for("main.index"))
    return render_template("login.html", next=next_url)


# 監査ログ挿入関数（DBパスはSCART_DB_PATH→SQLALCHEMY_DATABASE_URI→estimates.dbの順で取得）
def _insert_login_log(login_id, user_id, result):
    import os, sqlite3
    from flask import request, current_app
    db_path = os.environ.get("SCART_DB_PATH")
    if not db_path:
        uri = getattr(current_app, "config", {}).get("SQLALCHEMY_DATABASE_URI", "")
        if uri.startswith("sqlite:///"):
            db_path = uri.replace("sqlite:///", "", 1)
    if not db_path:
        db_path = "estimates.db"
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    try:
        conn = sqlite3.connect(db_path, timeout=10)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auth_login_log (login_id, user_id, result, ip, user_agent)
            VALUES (?, ?, ?, ?, ?)
            """,
            (login_id, user_id, result, ip, ua)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        try:
            current_app.logger.warning(f"auth_login_log insert failed: {e}")
        except Exception:
            pass

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("ログアウトしました。", "info")
    return redirect(url_for("auth.login"))



@auth_bp.route("/register", methods=["GET", "POST"])
@login_required
@roles_required("admin")
def register_user():
    if request.method == "POST":
        login_id = (request.form.get("login_id") or "").strip()
        display_name = (request.form.get("display_name") or "").strip()
        password = (request.form.get("password") or "").strip()
        role = (request.form.get("role") or "user").strip()
        # 承認制: 登録直後は is_active=0
        is_active = 0

        if not login_id or not display_name or not password:
            flash("必須項目が未入力です", "danger")
            return render_template("register.html", form=request.form)

        # approver 廃止：user / admin のみ許可
        if role not in ("user", "admin"):
            flash("権限(role)が不正です", "danger")
            return render_template("register.html", form=request.form)

        if User.query.filter_by(login_id=login_id).first():
            flash("同じログインIDが既に存在します", "danger")
            return render_template("register.html", form=request.form)

        try:
            u = User(
                login_id=login_id,
                display_name=display_name,
                password_hash=generate_password_hash(password),
                role=role,
                is_active=is_active,
                must_change_password=1,
            )
            db.session.add(u)
            db.session.commit()
            flash(f"ユーザーを登録しました: {login_id} ({role})", "success")
            return redirect(url_for("auth.register_user"))
        except Exception:
            db.session.rollback()
            flash("登録に失敗しました。ログを確認してください。", "danger")
            return render_template("register.html", form=request.form)
    # GET
    return render_template("register.html", form=None)

@auth_bp.route("/account/force_change", methods=["GET", "POST"])
@login_required
def force_change_password():
    user = g.current_user
    if not user:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        new_login_id = (request.form.get("login_id") or "").strip()
        new_password = (request.form.get("password") or "").strip()
        new_password2 = (request.form.get("password2") or "").strip()

        if not new_login_id or not new_password:
            flash("ログインIDとパスワードは必須です", "danger")
            return render_template("account_force_change.html", form=request.form)

        if new_password != new_password2:
            flash("パスワードが一致しません", "danger")
            return render_template("account_force_change.html", form=request.form)

        exists = User.query.filter(User.login_id == new_login_id, User.id != user.id).first()
        if exists:
            flash("同じログインIDが既に存在します", "danger")
            return render_template("account_force_change.html", form=request.form)

        try:
            user.login_id = new_login_id
            user.password_hash = generate_password_hash(new_password)
            user.must_change_password = 0
            user.password_changed_at = datetime.utcnow().isoformat()
            db.session.commit()
            flash("ユーザーIDとパスワードを更新しました", "success")
            return redirect(url_for("main.index"))
        except Exception:
            db.session.rollback()
            flash("更新に失敗しました。ログを確認してください。", "danger")

    return render_template("account_force_change.html", form={"login_id": user.login_id})


@auth_bp.route("/admin/users", methods=["GET"])
@login_required
@roles_required("admin")
def admin_user_list():
    users = User.query.order_by(User.id.desc()).all()
    return render_template("admin_user_list.html", users=users)


@auth_bp.route("/admin/users/<int:user_id>/reset", methods=["POST"])
@login_required
@roles_required("admin")
def admin_reset_user(user_id):
    user = User.query.get_or_404(user_id)

    # 事故防止：admin自身はリセット不可
    if user.login_id == "admin":
        flash("admin はリセットできません。", "danger")
        return redirect(url_for("auth.admin_user_list"))

    initial_password = "Temp1234!"
    try:
        user.password_hash = generate_password_hash(initial_password)
        user.must_change_password = 1
        user.password_reset_at = datetime.utcnow().isoformat()
        db.session.commit()
        flash("初期パスワードにリセットしました（ユーザーへ初期PWを連絡してください）", "warning")
    except Exception:
        db.session.rollback()
        flash("リセットに失敗しました。ログを確認してください。", "danger")
    return redirect(url_for("auth.admin_user_list"))
