from app import db
from sqlalchemy.orm import relationship



class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text, nullable=True)
    cost = db.Column(db.Float, nullable=False, default=0)  # 原価カラム

    details = relationship("QuotationDetail", back_populates="product")

    def __repr__(self):
        return f"<Product id={self.id} name={self.name} price={self.unit_price} cost={self.cost}>"

# 【開発メモ】
# カラム追加後、既存の app/db/scart.db を削除し、Flaskアプリ起動で自動再作成されます。
