from configs import db
from datetime import datetime


class StockItem(db.Model):
    __tablename__ = "stock_item"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material_id = db.Column(
        db.Integer, db.ForeignKey("material.id"), unique=True, nullable=False
    )
    qty_on_hand = db.Column(db.Numeric(18, 3), default=0)
    material = db.relationship("Material")


class StockMovement(db.Model):
    __tablename__ = "stock_movement"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    ref_type = db.Column(db.String(30))  # GRN/RETURN/ADJUSTMENT/ISSUE
    ref_id = db.Column(db.Integer)  # id tham chiếu (gr_line, return_line…)
    qty_change = db.Column(db.Numeric(18, 3), nullable=False)
    moved_at = db.Column(db.DateTime, default=datetime.utcnow)
    material = db.relationship("Material")
