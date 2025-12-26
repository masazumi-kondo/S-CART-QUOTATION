from flask import current_app
from datetime import datetime

def notify_customer_status_changed(customer, action, actor_user, comment):
    """
    Notify about customer approval/rejection event.
    Args:
        customer: Customer instance
        action: str (e.g. 'approved', 'rejected')
        actor_user: User instance or identifier
        comment: Optional string
    Behavior:
        - Log a one-line [NOTIFY] event
        - Build a payload for future email integration
        - Never break main flow (catch and log all exceptions)
    """
    try:
        # action正規化
        action_map = {'approved': 'approve', 'rejected': 'reject'}
        normalized_action = action_map.get(str(action), str(action))

        # actor情報
        actor_user_id = getattr(actor_user, 'id', None)
        actor_user_name = getattr(actor_user, 'username', None) or getattr(actor_user, 'name', None) or str(actor_user)

        # payload構築
        payload = {
            'customer_id': getattr(customer, 'id', None),
            'customer_name': getattr(customer, 'name', None),
            'customer_status': getattr(customer, 'status', None),
            'requested_by_user_id': getattr(customer, 'requested_by_user_id', None),
            'action': normalized_action,
            'actor': actor_user_name,
            'actor_user_id': actor_user_id,
            'actor_user_name': actor_user_name,
            'comment': comment,
            'comment_len': len(comment) if comment else 0,
            'timestamp_utc': datetime.utcnow().isoformat(),
        }
        current_app.logger.info(
            '[NOTIFY] action=%s customer_id=%s actor_user_id=%s status=%s',
            payload['action'], payload['customer_id'], payload['actor_user_id'], payload['customer_status']
        )
        # send_email(payload)  # 拡張点: 今は呼ばない
    except Exception as e:
        current_app.logger.exception('[NOTIFY] Notification failed: %s', e)

# メール送信スタブ（未使用、将来拡張用）
def send_email(payload):
    """
    Stub for future email notification.
    Args:
        payload: dict
    """
    pass
