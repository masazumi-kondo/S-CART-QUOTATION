from app import db
from datetime import datetime

class CustomerCredit(db.Model):
    __tablename__ = 'customer_credit'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    fiscal_year = db.Column(db.Integer, nullable=False)
    sales_amount = db.Column(db.Float)
    net_income = db.Column(db.Float)
    equity = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('customer_id', 'fiscal_year'),)

# Optional: Add relationship to Customer
from app.models.customer import Customer
Customer.credits = db.relationship('CustomerCredit', backref='customer', lazy='dynamic')
