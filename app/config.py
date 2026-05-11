import os

base_dir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(base_dir, "db")
os.makedirs(db_dir, exist_ok=True)
db_path = os.path.join(db_dir, "scart.db")

class Config:
    SECRET_KEY = "dev-secret-key"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email configuration
    MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "")
    
    # SMTP configuration
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME or "noreply@example.com")
    
    # Microsoft Graph API configuration
    GRAPH_TENANT_ID = os.environ.get("GRAPH_TENANT_ID", "")
    GRAPH_CLIENT_ID = os.environ.get("GRAPH_CLIENT_ID", "")
    GRAPH_CLIENT_SECRET = os.environ.get("GRAPH_CLIENT_SECRET", "")
    GRAPH_SENDER_USER = os.environ.get("GRAPH_SENDER_USER", "")
