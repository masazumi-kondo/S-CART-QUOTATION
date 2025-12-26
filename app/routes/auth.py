
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.auth_utils import login_required, roles_required

from app.models.user import User

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
        if user and user.check_password(password):
            if not user.is_active:
                flash("無効ユーザーです。", "danger")
                result = "inactive"
                user_id_val = user.id
            else:
                session["user_id"] = user.id
                flash("ログインしました。", "success")
                result = "success"
                user_id_val = user.id
                # オープンリダイレクト対策: next_urlが / で始まる場合のみ許可
                if next_url and next_url.startswith("/") and not next_url.startswith("//") and not next_url.startswith("/\\"):
                    _insert_login_log(login_id, user_id_val, result)
                    return redirect(next_url)
                else:
                    _insert_login_log(login_id, user_id_val, result)
                    return redirect(url_for("main.index"))
        else:
            flash("ログインIDまたはパスワードが違います。", "danger")
            result = "fail"
        _insert_login_log(login_id, user_id_val, result)
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
def register():
    from app import db
    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        display_name = request.form.get("display_name", "").strip()
        password = request.form.get("password", "")
        error = None
        if not login_id or not display_name or not password:
            error = "全ての項目を入力してください。"
        elif len(password) < 8:
            error = "パスワードは8文字以上で入力してください。"
        elif User.query.filter_by(login_id=login_id).first():
            error = "このログインIDは既に登録されています。"
        if error:
            flash(error, "danger")
            return render_template("register.html", login_id=login_id, display_name=display_name)
        try:
            user = User(
                login_id=login_id,
                display_name=display_name,
                role="user",
                is_active=False
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("ユーザー登録が完了しました。ログインしてください。", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            flash(f"登録に失敗しました: {e}", "danger")
            return render_template("register.html", login_id=login_id, display_name=display_name)
    return render_template("register.html")
