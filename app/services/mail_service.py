import smtplib
from email.message import EmailMessage
from flask import current_app


def is_mail_enabled():
    """Check if mail server is configured"""
    return bool(current_app.config.get("MAIL_SERVER"))


def send_email(to, subject, body):
    """
    Send a single email
    
    Args:
        to: Email address (str) or list of addresses
        subject: Email subject
        body: Email body (plain text)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not to:
        current_app.logger.warning("[MAIL] recipient is empty. subject=%s", subject)
        return False

    if not is_mail_enabled():
        current_app.logger.warning("[MAIL] MAIL_SERVER is not configured. skip sending. to=%s subject=%s", to, subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = current_app.config.get("MAIL_DEFAULT_SENDER")
    msg["To"] = to if isinstance(to, str) else ", ".join(to)
    msg.set_content(body)

    try:
        server = current_app.config.get("MAIL_SERVER")
        port = int(current_app.config.get("MAIL_PORT", 587))
        username = current_app.config.get("MAIL_USERNAME")
        password = current_app.config.get("MAIL_PASSWORD")
        use_tls = current_app.config.get("MAIL_USE_TLS", True)

        with smtplib.SMTP(server, port, timeout=10) as smtp:
            if use_tls:
                smtp.starttls()
            if username and password:
                smtp.login(username, password)
            smtp.send_message(msg)

        current_app.logger.info("[MAIL] sent. to=%s subject=%s", to, subject)
        return True

    except Exception as e:
        current_app.logger.exception("[MAIL] failed. to=%s subject=%s error=%s", to, subject, e)
        return False


def send_bulk_email(recipients, subject, body):
    """
    Send email to multiple recipients
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Email body
    
    Returns:
        True if all emails sent successfully, False otherwise
    """
    if not recipients:
        current_app.logger.warning("[MAIL] recipients is empty. subject=%s", subject)
        return False

    ok = True
    for recipient in recipients:
        result = send_email(recipient, subject, body)
        ok = ok and result

    return ok
