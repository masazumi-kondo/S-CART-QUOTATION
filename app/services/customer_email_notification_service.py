from flask import current_app, url_for
from app.services.mail_service import send_bulk_email, send_email
from app.services.notification_recipients import (
    get_customer_approval_admin_recipients,
    get_customer_approval_result_recipient,
)


def notify_customer_approval_request(customer):
    """
    Send approval request email to admins
    
    Args:
        customer: Customer object
    
    Returns:
        True if email sent successfully, False otherwise
    """
    recipients = get_customer_approval_admin_recipients()

    if not recipients:
        current_app.logger.warning("[CUSTOMER NOTIFY] no admin recipients for customer approval request. customer_id=%s", getattr(customer, "id", None))
        return False

    subject = "【見積アプリ】顧客マスタ承認依頼"

    customer_name = getattr(customer, "name", "") or ""
    
    # Get applicant info
    applicant = None
    applicant_id = getattr(customer, "requested_by_user_id", None)
    if applicant_id:
        from app.models.user import User
        applicant = User.query.get(applicant_id)
    
    applicant_name = getattr(applicant, "display_name", None) or getattr(applicant, "login_id", "") or "不明"

    try:
        approval_url = url_for("customer.customer_pending_list", _external=True)
    except Exception:
        approval_url = ""

    body = f"""顧客マスタの承認依頼があります。

申請者: {applicant_name}
顧客名: {customer_name}

以下の画面から内容を確認してください。
{approval_url}

※このメールは見積アプリから自動送信されています。"""

    return send_bulk_email(recipients, subject, body)


def notify_customer_approval_result(customer, result_label, comment=None):
    """
    Send approval result email to applicant
    
    Args:
        customer: Customer object
        result_label: Approval result label (e.g., "承認", "差し戻し", "却下")
        comment: Optional comment from admin
    
    Returns:
        True if email sent successfully, False otherwise
    """
    recipient = get_customer_approval_result_recipient(customer)

    if not recipient:
        current_app.logger.warning("[CUSTOMER NOTIFY] applicant cannot receive notification. customer_id=%s", getattr(customer, "id", None))
        return False

    customer_name = getattr(customer, "name", "") or ""
    subject = f"【見積アプリ】顧客マスタ申請結果：{result_label}"

    comment_text = comment or "なし"

    try:
        customer_url = url_for("customer.customer_list", _external=True)
    except Exception:
        customer_url = ""

    body = f"""顧客マスタ申請の結果をお知らせします。

顧客名: {customer_name}
結果: {result_label}
コメント: {comment_text}

以下の画面から内容を確認してください。
{customer_url}

※このメールは見積アプリから自動送信されています。"""

    return send_email(recipient, subject, body)
