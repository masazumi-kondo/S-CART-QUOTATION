
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
    discount_amount = db.Column(db.Integer, nullable=False, default=0)  # 値引き額を保存

    # 改定管理用
    original_id = db.Column(db.Integer, nullable=True, index=True)  # オリジナル見積ID（rev0は自分のid）
    revision_no = db.Column(db.Integer, nullable=False, default=0)  # 改定番号（rev0=0, 改定は1,2...）

    # --- new_v1 calculation columns (2025/12) ---
    calc_mode = db.Column(db.String, nullable=True)
    avg_entry_dirs = db.Column(db.Float, nullable=True)
    station_auto = db.Column(db.Integer, nullable=True)
    station_manual = db.Column(db.Integer, nullable=True)
    station_relay = db.Column(db.Integer, nullable=True)
    station_charge = db.Column(db.Integer, nullable=True)
    wait_position_count = db.Column(db.Integer, nullable=True)
    has_swap_operation = db.Column(db.Boolean, nullable=True)
    has_plc_handshake = db.Column(db.Boolean, nullable=True)
    has_ev_integration = db.Column(db.Boolean, nullable=True)
    difficulty_design = db.Column(db.String, nullable=True)
    difficulty_setup = db.Column(db.String, nullable=True)

    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=True, index=True)
    customer = relationship("Customer", back_populates="quotations")

    details = relationship(
        "QuotationDetail",
        back_populates="quotation",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Quotation id={self.id} project_name={self.project_name} estimator_name={self.estimator_name}>"
    
    @property
    def total_after_discount(self):
        """最終合計売価を計算"""
        total_sell = sum((d.subtotal or 0) for d in self.details) if self.details else 0
        discount_amount = (self.discount_amount or 0)
        return max(0, total_sell - discount_amount)

# --- 注意 ---
# この変更後は Flask サーバを再起動してください。
# 既存のDBに estimator_name カラムが無い場合は
# ・ALTER TABLE quotations ADD COLUMN estimator_name VARCHAR(100);
# または
# ・DBファイル(app/db/scart.db)を削除して再作成
# などの対応が必要です。
