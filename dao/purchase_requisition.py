from typing import Optional, List, Dict
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.purchase_requisition import (
    PurchaseRequisition,
    PRLine,
    PurchaseRequisitionStatus,
)


def get_pr_lines_as_dicts(pr_id: int) -> List[Dict]:
    """Trả về list dict [{'material_id':..,'qty':..}] từ PR."""
    lines: List[PRLine] = PRLine.query.filter_by(pr_id=pr_id).all()
    return [{"material_id": int(l.material_id), "qty": float(l.qty)} for l in lines]


def list_prs() -> List[PurchaseRequisition]:
    return PurchaseRequisition.query.order_by(PurchaseRequisition.id.desc()).all()


# Sửa hàm list_prs_approved (đang so sánh chuỗi) -> so enum
def list_prs_approved() -> List[PurchaseRequisition]:
    return (
        PurchaseRequisition.query.filter(
            PurchaseRequisition.status == PurchaseRequisitionStatus.APPROVED
        )
        .order_by(PurchaseRequisition.id.desc())
        .all()
    )


def get_pr(pr_id: int) -> Optional[PurchaseRequisition]:
    return PurchaseRequisition.query.get(pr_id)


def create_pr(requester_id: int, note: str | None, lines: List[Dict]):
    pr = PurchaseRequisition(requester_id=int(requester_id), note=note)
    db.session.add(pr)
    db.session.flush()  # có id
    for ln in lines:
        db.session.add(
            PRLine(pr_id=pr.id, material_id=ln["material_id"], qty=ln["qty"])
        )
    _commit()
    return pr


def update_pr(pr_id: int, requester_id: int, note: str | None, lines: List[Dict]):
    pr = PurchaseRequisition.query.get_or_404(pr_id)
    pr.requester_id = int(requester_id)
    pr.note = note
    # clear lines cũ
    PRLine.query.filter_by(pr_id=pr.id).delete()
    for ln in lines:
        db.session.add(
            PRLine(pr_id=pr.id, material_id=ln["material_id"], qty=ln["qty"])
        )
    _commit()
    return pr


def delete_pr(pr_id: int):
    pr = PurchaseRequisition.query.get_or_404(pr_id)
    db.session.delete(pr)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
