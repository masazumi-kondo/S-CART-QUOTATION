from flask import Blueprint, render_template, g, redirect, url_for, abort, current_app
from app.decorators import login_required
from app.models.notification import Notification
from app import db

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/notifications")
@login_required
def list_notifications():
    user_id = g.current_user.id

    items = (
        Notification.query
        .filter(Notification.user_id == user_id)
        .order_by(Notification.is_read.asc(), Notification.created_at.desc(), Notification.id.desc())
        .limit(200)
        .all()
    )

    unread_count = (
        Notification.query
        .filter(Notification.user_id == user_id, Notification.is_read == False)
        .count()
    )

    return render_template("notifications/list.html", notifications=items, unread_count=unread_count)


@notifications_bp.route("/notifications/<int:notification_id>/open", methods=["GET"])
@login_required
def notification_open(notification_id: int):
    user_id = g.current_user.id
    n = Notification.query.get_or_404(notification_id)

    if n.user_id != user_id:
        abort(403)

    # 既読化（失敗しても閲覧は継続）
    try:
        if not getattr(n, "is_read", False):
            n.is_read = True
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("[NOTIF] mark read failed: %s", e)

    link = (n.link or "").strip()
    if link.startswith("/") and not link.startswith("//") and not link.startswith("/\\"):
        return redirect(link)

    return redirect(url_for("notifications.list_notifications"))


# 互換用：旧 /read は open に寄せる（openで本人確認＋既読化）
@notifications_bp.route("/notifications/<int:notification_id>/read")
@login_required
def read_notification(notification_id: int):
    return redirect(url_for("notifications.notification_open", notification_id=notification_id), code=302)
