from app import db
from datetime import datetime

class LogicConfig(db.Model):
    __tablename__ = "logic_configs"

    id = db.Column(db.Integer, primary_key=True)
    design_rate = db.Column(db.Float, nullable=False)
    setup_rate = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
