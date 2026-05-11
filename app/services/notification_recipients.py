from app.models.user import User
from flask import current_app


def is_user_active(user):
    """Check if user is active"""
    if hasattr(user, "active"):
        return bool(user.active)
    if hasattr(user, "is_active"):
        attr = getattr(user, "is_active")
        return attr() if callable(attr) else bool(attr)
    return True


def can_receive_notification(user):
    """Check if user can receive notifications"""
    return bool(
        user
        and user.email
        and user.receive_notifications
        and is_user_active(user)
    )


def get_customer_approval_admin_recipients():
    """
    Get list of admin email addresses for customer approval notifications
    
    Returns:
        List of email addresses of active admins with notifications enabled
    """
    try:
        admins = User.query.filter_by(role="admin", receive_notifications=True).all()
        recipients = [
            user.email for user in admins
            if user.email and is_user_active(user)
        ]
        return recipients
    except Exception as e:
        current_app.logger.exception("[RECIPIENTS] failed to get admin recipients: %s", e)
        return []


def get_customer_approval_result_recipient(customer):
    """
    Get applicant's email for customer approval result notification
    
    Args:
        customer: Customer object
    
    Returns:
        Email address (str) or None if applicant cannot receive notification
    """
    try:
        applicant_id = getattr(customer, "requested_by_user_id", None)
        if not applicant_id:
            current_app.logger.warning("[RECIPIENTS] applicant_id missing for customer_id=%s", getattr(customer, "id", None))
            return None
        
        applicant = User.query.get(applicant_id)
        if can_receive_notification(applicant):
            return applicant.email
        else:
            current_app.logger.info("[RECIPIENTS] applicant cannot receive notification. user_id=%s", applicant_id)
            return None
    except Exception as e:
        current_app.logger.exception("[RECIPIENTS] failed to get result recipient: %s", e)
        return None
