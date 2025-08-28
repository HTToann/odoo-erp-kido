# db/models/invoice_payment.py
from configs import db
from datetime import datetime
import enum


class PaymentStatus(enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    CANCELED = "CANCELED"


class VendorInvoice(db.Model):
    __tablename__ = "vendor_invoice"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    po_id = db.Column(db.Integer, db.ForeignKey("purchase_order.id"))
    issued_at = db.Column(db.Date)  # ngày hóa đơn (nếu cần, form có thể bổ sung)
    status = db.Column(
        db.Enum(PaymentStatus), default=PaymentStatus.DRAFT, nullable=False
    )
    total = db.Column(db.Numeric(18, 2), default=0)  # tổng tiền từ các line

    supplier = db.relationship("Supplier")
    po = db.relationship("PurchaseOrder")
    lines = db.relationship(
        "InvoiceLine",
        backref=db.backref("invoice"),
        cascade="all, delete-orphan",
        lazy="joined",
    )
    payments = db.relationship(
        "Payment",
        backref=db.backref("invoice"),
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InvoiceLine(db.Model):
    __tablename__ = "invoice_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("vendor_invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    qty = db.Column(db.Numeric(18, 3), default=0)
    price = db.Column(db.Numeric(18, 2), default=0)
    line_total = db.Column(db.Numeric(18, 2), default=0)

    material = db.relationship("Material")


class Payment(db.Model):
    __tablename__ = "payment"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("vendor_invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount = db.Column(db.Numeric(18, 2), nullable=False)
    method = db.Column(db.String(30))  # bank/cash/...
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.Text)
