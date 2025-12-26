
from app import db
from sqlalchemy.orm import relationship
from datetime import datetime

class Quotation(db.Model):
    __tablename__ = "quotations"

    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    contact_name = db.Column(db.String(100), nullable=True)
    project_name = db.Column(db.String(200), nullable=False)
    delivery_date = db.Column(db.String(50), nullable=True)
    delivery_terms = db.Column(db.String(100), nullable=True)
    payment_terms = db.Column(db.String(100), nullable=True)
    valid_until = db.Column(db.String(50), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    estimator_name = db.Column(db.String(100), nullable=True)  # 見積作成担当者名を追加
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    discount_rate = db.Column(db.Float, nullable=False, default=0.0)  # 値引率(%)を保存

    # 改定管理用
    original_id = db.Column(db.Integer, nullable=True, index=True)  # オリジナル見積ID（rev0は自分のid）
    revision_no = db.Column(db.Integer, nullable=False, default=0)  # 改定番号（rev0=0, 改定は1,2...）


    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    customer = relationship("Customer", back_populates="quotations")

    details = relationship(
        "QuotationDetail",
        back_populates="quotation",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Quotation id={self.id} project_name={self.project_name} estimator_name={self.estimator_name}>"

# --- 注意 ---
# この変更後は Flask サーバを再起動してください。
# 既存のDBに estimator_name カラムが無い場合は
# ・ALTER TABLE quotations ADD COLUMN estimator_name VARCHAR(100);
# または
# ・DBファイル(app/db/scart.db)を削除して再作成
# などの対応が必要です。
