
from app import db
from datetime import datetime
from enum import Enum

# 顧客ステータス列挙（テンプレ/Jinja互換のためstr継承）
class CustomerStatus(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    acted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

from app import db
from datetime import datetime
from sqlalchemy.orm import relationship

class TransactionType(db.Model):
    __tablename__ = 'transaction_types'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    note = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    customers = relationship('Customer', back_populates='transaction_type_ref')

    def __repr__(self):
        return f'<TransactionType {self.code}:{self.name}>'

class PaymentTerm(db.Model):
    __tablename__ = 'payment_terms'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    customers = relationship('Customer', back_populates='payment_term_ref')

    def __repr__(self):
        return f'<PaymentTerm {self.code}:{self.name}>'

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(50))  # 得意先コード（自由入力）
    name = db.Column(db.String(255), unique=True, nullable=False)
    name_kana = db.Column(db.String(255))
    postal_code = db.Column(db.String(20))    # 郵便番号
    address = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    transaction_type = db.Column(db.String(50))  # 取引区分（旧）
    payment_terms = db.Column(db.String(100))    # 支払条件（旧）
    transaction_type_id = db.Column(db.Integer, db.ForeignKey('transaction_types.id'), nullable=True)
    payment_term_id = db.Column(db.Integer, db.ForeignKey('payment_terms.id'), nullable=True)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 削除カラム: contact_name, email（既存カラムは削除しない指示のため残すが、今後未使用）
    contact_name = db.Column(db.String(255))
    email = db.Column(db.String(255))

    # 承認フロー用カラム
    status = db.Column(db.String(20), nullable=False, default="approved")
    requested_by_user_id = db.Column(db.Integer, nullable=True)
    approved_by_user_id = db.Column(db.Integer, nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    approval_comment = db.Column(db.Text, nullable=True)

    quotations = relationship("Quotation", back_populates="customer")
    transaction_type_ref = relationship('TransactionType', back_populates='customers')
    payment_term_ref = relationship('PaymentTerm', back_populates='customers')

    @property
    def is_pending(self):
        return self.status == CustomerStatus.PENDING.value

    @property
    def is_approved(self):
        return self.status == CustomerStatus.APPROVED.value

    @property
    def is_rejected(self):
        return self.status == CustomerStatus.REJECTED.value

    def __repr__(self):
        return f'<Customer {self.name}>'
