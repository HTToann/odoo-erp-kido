from configs import db
from datetime import datetime
import enum


class POStatus(enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_order"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    po_no = db.Column(db.String(40), unique=True, nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    supplier = db.relationship("Supplier", backref="purchase_orders")

    status = db.Column(
        db.Enum(POStatus, name="postatus"), default=POStatus.DRAFT, nullable=False
    )
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_date = db.Column(db.DateTime)

    subtotal = db.Column(db.Numeric(18, 2), default=0)
    tax = db.Column(db.Numeric(18, 2), default=0)
    total = db.Column(db.Numeric(18, 2), default=0)
    vq_id = db.Column(db.Integer, db.ForeignKey("vendor_quotation.id"))
    vq = db.relationship("VendorQuotation", backref=db.backref("po", uselist=False))


class PurchaseOrderItem(db.Model):
    __tablename__ = "purchase_order_item"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    po_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_order.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)

    qty = db.Column(db.Numeric(18, 3), nullable=False)
    price = db.Column(db.Numeric(18, 2), nullable=False)
    line_total = db.Column(db.Numeric(18, 2), nullable=False)

    po = db.relationship("PurchaseOrder", backref="items")
    material = db.relationship("Material")
