"""Service for generating mailto URLs for customer notifications"""
from flask import current_app, url_for
from app.services.mailto_service import build_mailto_url
from app.services.notification_recipients import (
    get_customer_approval_admin_recipients,
    get_customer_approval_result_recipient,
)


def build_customer_approval_request_mailto(customer):
    """
    Generate mailto URL for customer approval request email.
    
    This allows users to open Outlook with pre-filled approval request message.
    
    Args:
        customer: Customer object
    
    Returns:
        mailto URL string or None if no recipients or invalid config
    """
    recipients = get_customer_approval_admin_recipients()

    if not recipients:
        current_app.logger.warning("[CUSTOMER MAILTO] no admin recipients for approval request. customer_id=%s", getattr(customer, "id", None))
        return None

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
        approval_url = "(アプリのメニュー > 顧客承認)"

    subject = "【見積アプリ】顧客マスタ承認依頼"

    body = f"""顧客マスタの承認依頼があります。

申請者: {applicant_name}
顧客名: {customer_name}

以下の画面から内容を確認してください。
{approval_url}

※このメールは見積アプリから作成されています。"""

    return build_mailto_url(recipients, subject, body)


def build_customer_approval_result_mailto(customer, result_label, comment=None):
    """
    Generate mailto URL for customer approval result email.
    
    This allows admins to open Outlook with pre-filled result notification message.
    
    Args:
        customer: Customer object
        result_label: Approval result label (e.g., "承認", "却下")
        comment: Optional comment from admin
    
    Returns:
        mailto URL string or None if no recipient or invalid config
    """
    recipient = get_customer_approval_result_recipient(customer)

    if not recipient:
        current_app.logger.warning("[CUSTOMER MAILTO] applicant cannot receive notification. customer_id=%s", getattr(customer, "id", None))
        return None

    customer_name = getattr(customer, "name", "") or ""
    subject = f"【見積アプリ】顧客マスタ申請結果：{result_label}"

    comment_text = comment or "なし"

    try:
        customer_url = url_for("customer.customer_list", _external=True)
    except Exception:
        customer_url = "(アプリのメニュー > 顧客マスタ)"

    body = f"""顧客マスタ申請の結果をお知らせします。

顧客名: {customer_name}
結果: {result_label}
コメント: {comment_text}

以下の画面から内容を確認してください。
{customer_url}

※このメールは見積アプリから作成されています。"""

    return build_mailto_url(recipient, subject, body)
