from app import db
from datetime import datetime


class CustomerApprovalLog(db.Model):
    __tablename__ = "customer_approval_log"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    approved_by = db.Column(db.Integer, nullable=False)
    approved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
