from typing import Optional, List, Dict
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.rfq import RFQ, RFQLine, RFQStatus
from dao import purchase_requisition as pr_dao

# Map string từ form -> Enum RFQStatus (nhận cả alias UI cũ)
_FORM_TO_ENUM = {
    "draft": RFQStatus.DRAFT,
    "submitted": RFQStatus.SUBMITTED,
    "approved": RFQStatus.APPROVED,
    "rejected": RFQStatus.REJECTED,
}


def build_lines_from_pr(pr_id: int) -> List[Dict]:
    """Chuẩn bị lines cho RFQ dựa trên PR."""
    return pr_dao.get_pr_lines_as_dicts(pr_id)


def get_rfq_lines_as_dicts(rfq_id: int) -> List[Dict]:
    """Trả về list dict [{'material_id':..,'qty':..}] từ RFQ."""
    lines: List[RFQLine] = RFQLine.query.filter_by(rfq_id=rfq_id).all()
    return [{"material_id": int(l.material_id), "qty": float(l.qty)} for l in lines]


def create_rfq_from_pr(pr_id: int, status: str = "draft") -> RFQ:
    """Tạo RFQ và copy toàn bộ dòng từ PR."""
    lines = build_lines_from_pr(pr_id)
    return create_rfq(pr_id=pr_id, status=status, lines=lines)


def _to_rfq_status(value: str | None) -> RFQStatus:
    if not value:
        return RFQStatus.DRAFT
    return _FORM_TO_ENUM.get(value.strip().lower(), RFQStatus.DRAFT)


def list_rfqs() -> List[RFQ]:
    return RFQ.query.order_by(RFQ.id.desc()).all()


def get_rfq(rfq_id: int) -> Optional[RFQ]:
    return RFQ.query.get(rfq_id)


def create_rfq(pr_id: int | None, status: str, lines: List[Dict]) -> RFQ:
    if not pr_id:
        raise ValueError(
            "❌ Không thể tạo RFQ khi chưa chọn Purchase Requisition (PR)."
        )

    r = RFQ(
        pr_id=int(pr_id),
        status=_to_rfq_status(status),
    )
    db.session.add(r)
    db.session.flush()  # có r.id để insert RFQLine

    for ln in lines or []:
        db.session.add(
            RFQLine(
                rfq_id=r.id,
                material_id=ln["material_id"],
                qty=ln["qty"],
            )
        )

    _commit()
    return r


def update_rfq(rfq_id: int, pr_id: int | None, status: str, lines: List[Dict]) -> RFQ:
    r = RFQ.query.get_or_404(rfq_id)
    r.pr_id = int(pr_id) if pr_id else None
    r.status = _to_rfq_status(status)

    # replace toàn bộ lines
    RFQLine.query.filter_by(rfq_id=r.id).delete()
    for ln in lines or []:
        db.session.add(
            RFQLine(
                rfq_id=r.id,
                material_id=ln["material_id"],
                qty=ln["qty"],
            )
        )

    _commit()
    return r


def delete_rfq(rfq_id: int):
    r = RFQ.query.get_or_404(rfq_id)
    db.session.delete(r)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
