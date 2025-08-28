# db/models/purchase_return.py
from configs import db
import enum
from datetime import datetime


class PurchaseReturnStatus(enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RETURNED = "RETURNED"
    POSTED = "POSTED"


class PurchaseReturn(db.Model):
    __tablename__ = "purchase_return"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gr_id = db.Column(db.Integer, db.ForeignKey("goods_receipt.id"), nullable=False)
    status = db.Column(
        db.Enum(PurchaseReturnStatus),
        default=PurchaseReturnStatus.DRAFT,
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    gr = db.relationship("GoodsReceipt")
    lines = db.relationship(
        "ReturnLine",
        backref="return_doc",
        cascade="all, delete-orphan",
        lazy="joined",
    )


class ReturnLine(db.Model):
    __tablename__ = "return_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    return_id = db.Column(
        db.Integer,
        db.ForeignKey("purchase_return.id", ondelete="CASCADE"),
        nullable=False,
    )
    gr_line_id = db.Column(db.Integer, db.ForeignKey("gr_line.id"), nullable=False)
    qty = db.Column(db.Numeric(18, 3), nullable=False)
    reason = db.Column(db.Text)

    gr_line = db.relationship("GRLine")
