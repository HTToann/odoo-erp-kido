from configs import db
import enum


class RFQStatus(enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RFQ(db.Model):
    __tablename__ = "rfq"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pr_id = db.Column(db.Integer, db.ForeignKey("purchase_requisition.id"))
    status = db.Column(
        db.Enum(RFQStatus), default=RFQStatus.DRAFT, nullable=False
    )  # draft/submitted/approved/rejected

    pr = db.relationship("PurchaseRequisition")

    # KHÔNG backref ở đây, dùng back_populates khớp với VendorQuotation.rfq
    vqs = db.relationship(
        "VendorQuotation",
        back_populates="rfq",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
    )


class RFQLine(db.Model):
    __tablename__ = "rfq_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rfq_id = db.Column(
        db.Integer, db.ForeignKey("rfq.id", ondelete="CASCADE"), nullable=False
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    qty = db.Column(db.Numeric(18, 3), nullable=False)

    rfq = db.relationship(
        "RFQ",
        backref=db.backref(
            "lines", cascade="all, delete-orphan", lazy="select", passive_deletes=True
        ),
    )
    material = db.relationship("Material")
