"""Service for generating mailto URLs for Outlook"""
from urllib.parse import quote


def build_mailto_url(to, subject, body):
    """
    Generate a mailto URL for opening Outlook with pre-filled content.
    
    Args:
        to: Single email address or list of email addresses
        subject: Email subject
        body: Email body (newlines will be encoded)
    
    Returns:
        mailto URL string or None if invalid
    
    Example:
        url = build_mailto_url("admin@example.com", "Test", "Hello")
        # mailto:admin@example.com?subject=Test&body=Hello
    """
    if not to:
        return None
    
    # Convert list to comma-separated string
    if isinstance(to, list):
        to_part = ",".join([addr.strip() for addr in to if addr and addr.strip()])
    else:
        to_part = str(to).strip()
    
    if not to_part:
        return None
    
    # Encode subject and body
    subject_encoded = quote(subject or "")
    body_encoded = quote(body or "")
    
    # Build mailto URL (email addresses have special handling for @ and .)
    return f"mailto:{quote(to_part, safe='@,.;+-_')}?subject={subject_encoded}&body={body_encoded}"
