from app import db
from sqlalchemy.orm import relationship



class QuotationDetail(db.Model):
    __tablename__ = "quotation_details"

    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey("quotations.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    label = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Float, nullable=False)  # 数量は float 型
    price = db.Column(db.Float, nullable=False)
    profit_rate = db.Column(db.Float, nullable=True)
    subtotal = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=True)  # 品名・仕様

    quotation = relationship("Quotation", back_populates="details")
    product = relationship("Product", back_populates="details")

# 【開発メモ】
# QuotationDetail モデルを変更した場合は app/db/scart.db を削除し、
# Flask アプリ起動時の db.create_all() で DB を再作成してください
# （開発中で既存データが不要な場合）。
