"""Email notification service for quotation approvals"""
from flask import current_app, url_for
from app.services.mail_service import send_bulk_email


def notify_quotation_approval_request(quotation):
    """
    Send approval request email to admins when a quotation is submitted for approval.
    
    Args:
        quotation: Quotation object
    
    Returns:
        True if email sent successfully, False otherwise
    """
    from app.services.notification_recipients import get_approval_notification_users
    
    users = get_approval_notification_users()
    recipients = [user.email for user in users if user.email]

    if not recipients:
        current_app.logger.warning("[QUOTATION NOTIFY] no admin recipients for quotation approval request. quotation_id=%s", getattr(quotation, "id", None))
        return False

    subject = "【見積アプリ】見積承認依頼"

    # Get quotation details
    quotation_no = getattr(quotation, "quotation_no", "") or ""
    customer = getattr(quotation, "customer", None)
    customer_name = getattr(customer, "name", "") if customer else ""
    project_name = getattr(quotation, "project_name", "") or ""
    
    # Get applicant info (estimator)
    estimator = getattr(quotation, "estimator_user", None)
    estimator_name = getattr(estimator, "display_name", None) or getattr(estimator, "login_id", "") or "不明" if estimator else "不明"

    try:
        approval_url = url_for("quotation.quotation_list", _external=True)
    except Exception:
        approval_url = ""

    body = f"""見積の承認依頼があります。

見積No.: {quotation_no}
顧客名: {customer_name}
案件名: {project_name}
申請者: {estimator_name}

以下の画面から内容を確認してください。
{approval_url}

※このメールは見積アプリから自動送信されています。"""

    return send_bulk_email(recipients, subject, body)
