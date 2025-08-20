# dao/purchase_return.py
from typing import Optional, List, Dict
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.purchase_return import PurchaseReturn, ReturnLine, PurchaseReturnStatus

# Map giá trị từ form (lowercase) -> Enum (UPPERCASE)
_RET_FORM_TO_ENUM = {
    "draft": PurchaseReturnStatus.DRAFT,
    "approved": PurchaseReturnStatus.APPROVED,
    "returned": PurchaseReturnStatus.RETURNED,
    "posted": PurchaseReturnStatus.POSTED,
}


def _to_ret_status(value: str | None) -> PurchaseReturnStatus:
    if not value:
        return PurchaseReturnStatus.DRAFT
    return _RET_FORM_TO_ENUM.get(value.strip().lower(), PurchaseReturnStatus.DRAFT)


def list_returns() -> List[PurchaseReturn]:
    return PurchaseReturn.query.order_by(PurchaseReturn.id.desc()).all()


def get_return(return_id: int) -> Optional[PurchaseReturn]:
    # nếu muốn hết cảnh báo legacy: return db.session.get(PurchaseReturn, return_id)
    return PurchaseReturn.query.get(return_id)


def create_return(gr_id: int, status: str, lines: List[Dict]) -> PurchaseReturn:
    r = PurchaseReturn(gr_id=int(gr_id), status=_to_ret_status(status))
    db.session.add(r)
    db.session.flush()
    for ln in lines or []:
        db.session.add(
            ReturnLine(
                return_id=r.id,
                gr_line_id=int(ln["gr_line_id"]),
                qty=ln["qty"],
                reason=ln.get("reason"),
            )
        )
    _commit()
    return r


def update_return(
    return_id: int, gr_id: int, status: str, lines: List[Dict]
) -> PurchaseReturn:
    r = PurchaseReturn.query.get_or_404(return_id)
    r.gr_id = int(gr_id)
    r.status = _to_ret_status(status)
    ReturnLine.query.filter_by(return_id=r.id).delete()
    for ln in lines or []:
        db.session.add(
            ReturnLine(
                return_id=r.id,
                gr_line_id=int(ln["gr_line_id"]),
                qty=ln["qty"],
                reason=ln.get("reason"),
            )
        )
    _commit()
    return r


def delete_return(return_id: int) -> None:
    r = PurchaseReturn.query.get_or_404(return_id)
    db.session.delete(r)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
