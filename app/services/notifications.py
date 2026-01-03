
import logging
from flask import url_for
from app import db
from app.models.notification import Notification

logger = logging.getLogger(__name__)

def notify_customer_status_changed(customer, action: str, actor_user=None, comment: str = ""):
    """
    顧客ステータス変更通知（最小実装）
    - DBに通知を保存（宛先=申請者）
    - メール送信等は後で差し替え可能
    """
    try:
        # 申請者
        requester_id = getattr(customer, "requested_by_user_id", None)
        if not requester_id:
            logger.info("[NOTIFY] skip: requester_id missing (customer_id=%s)", getattr(customer, "id", None))
            return

        # 自分が自分を却下/承認したケースは通知不要（ノイズ削減）
        actor_id = getattr(actor_user, "id", None) if actor_user else None
        if actor_id and actor_id == requester_id:
            logger.info("[NOTIFY] skip: actor==requester (user_id=%s)", actor_id)
            return

        company = getattr(customer, "name", "") or ""
        cid = getattr(customer, "id", None)

        if action == "reject":
            title = "顧客申請が却下されました"
            message = f"顧客「{company}」が却下されました。"
            if comment:
                message += f"\n理由: {comment}"
        elif action == "approve":
            title = "顧客申請が承認されました"
            message = f"顧客「{company}」が承認されました。"
        else:
            logger.info("[NOTIFY] skip: unknown action=%s", action)
            return

        # 申請者は pending でも edit を閲覧可にしている前提
        link = url_for("customer.customer_edit", customer_id=cid) if cid else None

        n = Notification(
            user_id=requester_id,
            title=title,
            message=message,
            link=link,
            is_read=False,
        )
        db.session.add(n)
        db.session.commit()

        logger.info("[NOTIFY] saved: user_id=%s action=%s customer_id=%s", requester_id, action, cid)

    except Exception as e:
        db.session.rollback()
        logger.exception("[NOTIFY] failed: %s", e)
        return

# メール送信スタブ（未使用、将来拡張用）
def send_email(payload):
    """
    Stub for future email notification.
    Args:
        payload: dict
    """
    pass
