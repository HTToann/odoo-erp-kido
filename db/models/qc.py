from sqlalchemy import DateTime
from configs import db
import enum


class QCStatus(enum.Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class QCReport(db.Model):
    __tablename__ = "qc_report"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gr_id = db.Column(db.Integer, db.ForeignKey("goods_receipt.id"), nullable=False)

    status = db.Column(
        db.Enum(QCStatus), default=QCStatus.PENDING, nullable=False
    )  # pending/passed/failed
    checked_at = db.Column(DateTime(timezone=True), nullable=True, index=True)
    gr = db.relationship("GoodsReceipt")


class QCLine(db.Model):
    __tablename__ = "qc_line"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    qc_id = db.Column(
        db.Integer, db.ForeignKey("qc_report.id", ondelete="CASCADE"), nullable=False
    )
    gr_line_id = db.Column(db.Integer, db.ForeignKey("gr_line.id"), nullable=False)
    result = db.Column(db.String(10))  # pass/fail
    accepted_qty = db.Column(db.Numeric(18, 3), default=0)
    note = db.Column(db.Text)
    qc = db.relationship(
        "QCReport", backref=db.backref("lines", cascade="all, delete-orphan")
    )
    gr_line = db.relationship("GRLine")
