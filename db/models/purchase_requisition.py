from configs import db
import enum


class PurchaseRequisitionStatus(enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PurchaseRequisition(db.Model):
    __tablename__ = "purchase_requisition"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # dept_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False)
    requester_id = db.Column(
        db.Integer, db.ForeignKey("user_account.id"), nullable=False
    )
    status = db.Column(
        db.Enum(PurchaseRequisitionStatus),
        default=PurchaseRequisitionStatus.DRAFT,
        nullable=False,
    )  # draft/submitted/approved/rejected
    note = db.Column(db.Text)
    # department = db.relationship("Department")
    requester = db.relationship("User")


class PRLine(db.Model):
    __tablename__ = "pr_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    pr_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_requisition.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = db.Column(db.Integer, db.ForeignKey("material.id"), nullable=False)
    qty = db.Column(db.Numeric(18, 3), nullable=False)
    pr = db.relationship(
        "PurchaseRequisition", backref=db.backref("lines", cascade="all, delete-orphan")
    )
    material = db.relationship("Material")
