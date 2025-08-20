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
    status = db.Column(
        db.Enum(PaymentStatus, name="paymentstatus"),
        default=PaymentStatus.DRAFT,
        nullable=False,
    )
    total = db.Column(db.Numeric(18, 2), default=0)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)

    supplier = db.relationship("Supplier")
    po = db.relationship("PurchaseOrder")


class InvoiceLine(db.Model):
    __tablename__ = "invoice_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(
        db.Integer,
        db.ForeignKey("vendor_invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"))
    qty = db.Column(db.Numeric(18, 3), nullable=False)
    price = db.Column(db.Numeric(18, 2), nullable=False)
    line_total = db.Column(db.Numeric(18, 2), nullable=False)

    invoice = db.relationship(
        "VendorInvoice", backref=db.backref("lines", cascade="all, delete-orphan")
    )
    material = db.relationship("Material")


class Payment(db.Model):
    __tablename__ = "payment"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(
        db.Integer, db.ForeignKey("vendor_invoice.id"), nullable=False
    )
    amount = db.Column(db.Numeric(18, 2), nullable=False)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    method = db.Column(db.String(30))
    invoice = db.relationship("VendorInvoice")
