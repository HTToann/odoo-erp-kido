from configs import db
from datetime import datetime
import enum


class GRStatus(enum.Enum):
    DRAFT = "DRAFT"
    CHECKED = "CHECKED"
    POSTED = "POSTED"


class GoodsReceipt(db.Model):
    __tablename__ = "goods_receipt"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    po_id = db.Column(db.Integer, db.ForeignKey("purchase_order.id"), nullable=False)
    status = db.Column(
        db.Enum(GRStatus, name="grstatus"), default=GRStatus.DRAFT, nullable=False
    )  # draft/checked/posted
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    po = db.relationship("PurchaseOrder")


class GRLine(db.Model):
    __tablename__ = "gr_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gr_id = db.Column(
        db.Integer,
        db.ForeignKey("goods_receipt.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    po_line_id = db.Column(db.Integer, db.ForeignKey("purchase_order_item.id"))
    qty = db.Column(db.Numeric(18, 3), nullable=False)
    gr = db.relationship(
        "GoodsReceipt", backref=db.backref("lines", cascade="all, delete-orphan")
    )
    material = db.relationship("Material")
    po_line = db.relationship("PurchaseOrderItem")
