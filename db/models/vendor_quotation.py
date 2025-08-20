from configs import db
import enum


class VendorQuotationStatus(enum.Enum):
    RECEIVED = "RECEIVED"
    SELECTED = "SELECTED"
    REJECTED = "REJECTED"


class VendorQuotation(db.Model):
    __tablename__ = "vendor_quotation"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rfq_id = db.Column(
        db.Integer, db.ForeignKey("rfq.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id = db.Column(db.Integer, db.ForeignKey("supplier.id"), nullable=False)
    status = db.Column(
        db.Enum(VendorQuotationStatus),
        default=VendorQuotationStatus.RECEIVED,
        nullable=False,
    )  # received/selected/rejected

    # Ghép với RFQ.vqs
    rfq = db.relationship("RFQ", back_populates="vqs")
    supplier = db.relationship("Supplier")


class VendorQuotationLine(db.Model):
    __tablename__ = "vendor_quotation_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vq_id = db.Column(
        db.Integer,
        db.ForeignKey("vendor_quotation.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    qty = db.Column(db.Numeric(18, 3), nullable=False)
    price = db.Column(db.Numeric(18, 2), nullable=False)

    vq = db.relationship(
        "VendorQuotation",
        backref=db.backref(
            "lines", cascade="all, delete-orphan", lazy="select", passive_deletes=True
        ),
    )
    material = db.relationship("Material")
