from app import db
from datetime import datetime


class CustomerApprovalLog(db.Model):
    __tablename__ = "customer_approval_log"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    approved_by = db.Column(db.Integer, nullable=False)
    approved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    action = db.Column(db.Text, nullable=False, default="approve")
    comment = db.Column(db.Text)
    actor_user_id = db.Column(db.Integer, nullable=True)
    actor_username = db.Column(db.String(255), nullable=True)
    actor_role = db.Column(db.String(50), nullable=True)
    ip_addr = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
