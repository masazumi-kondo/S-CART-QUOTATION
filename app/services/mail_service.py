import smtplib
from email.message import EmailMessage
from flask import current_app


def is_mail_enabled():
    """Check if mail server is configured"""
    return bool(current_app.config.get("MAIL_SERVER"))


def send_smtp_email(to, subject, body):
    """
    Send a single email using SMTP
    
    Args:
        to: Email address (str) or list of addresses
        subject: Email subject
        body: Email body (plain text)
    
    Returns:
        True if sent successfully, False otherwise
    """
    if not to:
        current_app.logger.warning("[SMTP MAIL] recipient is empty. subject=%s", subject)
        return False

    if not is_mail_enabled():
        current_app.logger.warning("[SMTP MAIL] MAIL_SERVER is not configured. skip sending. to=%s subject=%s", to, subject)
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

        current_app.logger.info("[SMTP MAIL] sent. to=%s subject=%s", to, subject)
        return True

    except Exception as e:
        current_app.logger.exception("[SMTP MAIL] failed. to=%s subject=%s error=%s", to, subject, e)
        return False


def send_smtp_bulk_email(recipients, subject, body):
    """
    Send email to multiple recipients using SMTP
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Email body
    
    Returns:
        True if all emails sent successfully, False otherwise
    """
    if not recipients:
        current_app.logger.warning("[SMTP MAIL] recipients is empty. subject=%s", subject)
        return False

    ok = True
    for recipient in recipients:
        result = send_smtp_email(recipient, subject, body)
        ok = ok and result

    return ok


def send_email(to, subject, body):
    """
    Send email using configured provider (Graph API or SMTP)
    
    Args:
        to: Email address (str) or list of addresses
        subject: Email subject
        body: Email body
    
    Returns:
        True if sent successfully, False otherwise
    """
    provider = current_app.config.get("MAIL_PROVIDER", "").lower()

    if provider == "graph":
        try:
            from app.services.graph_mail_service import send_graph_email
            return send_graph_email(to, subject, body)
        except ImportError:
            current_app.logger.error("[MAIL] graph_mail_service import failed. falling back to skip.")
            return False

    if provider == "smtp":
        return send_smtp_email(to, subject, body)

    current_app.logger.warning("[MAIL] MAIL_PROVIDER is not configured or unknown. skip. to=%s subject=%s", to, subject)
    return False


def send_bulk_email(recipients, subject, body):
    """
    Send email to multiple recipients using configured provider
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Email body
    
    Returns:
        True if all emails sent successfully, False otherwise
    """
    provider = current_app.config.get("MAIL_PROVIDER", "").lower()

    if provider == "graph":
        try:
            from app.services.graph_mail_service import send_graph_bulk_email
            return send_graph_bulk_email(recipients, subject, body)
        except ImportError:
            current_app.logger.error("[MAIL] graph_mail_service import failed. falling back to skip.")
            return False

    if provider == "smtp":
        return send_smtp_bulk_email(recipients, subject, body)

    current_app.logger.warning("[MAIL] MAIL_PROVIDER is not configured or unknown. skip. recipients=%s subject=%s", recipients, subject)
    return False
