import requests
import msal
from flask import current_app

GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]


def get_graph_mail_config_status():
    """Get the status of Graph mail configuration
    
    Returns:
        dict with configuration status (True/False for each setting)
    """
    return {
        "GRAPH_TENANT_ID": bool(current_app.config.get("GRAPH_TENANT_ID")),
        "GRAPH_CLIENT_ID": bool(current_app.config.get("GRAPH_CLIENT_ID")),
        "GRAPH_CLIENT_SECRET": bool(current_app.config.get("GRAPH_CLIENT_SECRET")),
        "GRAPH_SENDER_USER": bool(current_app.config.get("GRAPH_SENDER_USER")),
    }


def get_graph_mail_missing_settings():
    """Get list of missing Graph mail settings
    
    Returns:
        list of missing configuration keys
    """
    required = [
        "GRAPH_TENANT_ID",
        "GRAPH_CLIENT_ID",
        "GRAPH_CLIENT_SECRET",
        "GRAPH_SENDER_USER",
    ]
    missing = []
    for key in required:
        if not current_app.config.get(key):
            missing.append(key)
    return missing


def is_graph_mail_configured():
    """Check if Microsoft Graph mail is properly configured"""
    return len(get_graph_mail_missing_settings()) == 0


def get_graph_access_token():
    """Acquire access token using client credentials flow"""
    tenant_id = current_app.config.get("GRAPH_TENANT_ID")
    client_id = current_app.config.get("GRAPH_CLIENT_ID")
    client_secret = current_app.config.get("GRAPH_CLIENT_SECRET")

    authority = f"https://login.microsoftonline.com/{tenant_id}"

    try:
        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            authority=authority,
            client_credential=client_secret,
        )

        result = app.acquire_token_for_client(scopes=GRAPH_SCOPE)

        if "access_token" not in result:
            current_app.logger.error(
                "[GRAPH MAIL] token acquisition failed. error=%s description=%s correlation_id=%s",
                result.get("error", "unknown"),
                result.get("error_description", "no description"),
                result.get("correlation_id", "none"),
            )
            return None

        return result["access_token"]

    except Exception as e:
        current_app.logger.exception("[GRAPH MAIL] exception during token acquisition: %s", e)
        return None


def send_graph_email(to, subject, body):
    """
    Send email using Microsoft Graph API
    
    Args:
        to: Email address (str) or list of addresses
        subject: Email subject
        body: Email body (plain text)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not to:
        current_app.logger.warning("[GRAPH MAIL] recipient is empty. subject=%s", subject)
        return False

    if not is_graph_mail_configured():
        current_app.logger.warning("[GRAPH MAIL] graph mail is not configured. skip. to=%s subject=%s", to, subject)
        return False

    token = get_graph_access_token()
    if not token:
        current_app.logger.error("[GRAPH MAIL] failed to get access token")
        return False

    sender = current_app.config.get("GRAPH_SENDER_USER")
    endpoint = f"https://graph.microsoft.com/v1.0/users/{sender}/sendMail"

    recipients = to if isinstance(to, list) else [to]

    payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body,
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": email
                    }
                }
                for email in recipients
            ],
        },
        "saveToSentItems": "true",
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=15,
        )

        if response.status_code in (202, 200):
            current_app.logger.info("[GRAPH MAIL] sent successfully. to=%s subject=%s", recipients, subject)
            return True

        current_app.logger.error(
            "[GRAPH MAIL] send failed. status_code=%s response=%s",
            response.status_code,
            response.text[:500],  # Truncate response to avoid logging sensitive info
        )
        return False

    except Exception as e:
        current_app.logger.exception("[GRAPH MAIL] exception while sending. to=%s subject=%s error=%s", recipients, subject, e)
        return False


def send_graph_bulk_email(recipients, subject, body):
    """
    Send email to multiple recipients using Microsoft Graph API
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Email body
    
    Returns:
        True if all emails sent successfully, False otherwise
    """
    if not recipients:
        current_app.logger.warning("[GRAPH MAIL] recipients empty. subject=%s", subject)
        return False

    return send_graph_email(recipients, subject, body)
