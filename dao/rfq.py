from typing import Optional, List, Dict
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.rfq import RFQ, RFQLine, RFQStatus
from db.models.purchase_requisition import PurchaseRequisitionStatus  # <-- dùng enum PR
from dao import purchase_requisition as pr_dao

# Map string từ form -> Enum RFQStatus (nhận cả alias UI cũ)
_FORM_TO_ENUM = {
    "draft": RFQStatus.DRAFT,
    "submitted": RFQStatus.SUBMITTED,
    "approved": RFQStatus.APPROVED,
    "rejected": RFQStatus.REJECTED,
}


def _to_rfq_status(value: str | None) -> RFQStatus:
    if not value:
        return RFQStatus.DRAFT
    return _FORM_TO_ENUM.get((value or "").strip().lower(), RFQStatus.DRAFT)


# -------- helpers --------
def _require_approved_pr(pr_id: int):
    """Lấy PR và đảm bảo PR đã APPROVED; raise nếu sai."""
    if not pr_id:
        raise ValueError("Vui lòng chọn Purchase Requisition (PR).")
    pr = pr_dao.get_pr(int(pr_id))
    if not pr:
        raise ValueError("PR không tồn tại.")
    if pr.status != PurchaseRequisitionStatus.APPROVED:
        raise ValueError("Chỉ có thể tạo/ghi RFQ từ PR đã APPROVED.")
    return pr


def _normalize_lines(lines: List[Dict]) -> List[Dict]:
    """Chuẩn hoá & validate lines: material_id bắt buộc, qty > 0."""
    if not lines:
        raise ValueError("Vui lòng nhập ít nhất 1 dòng vật tư.")
    out: List[Dict] = []
    for idx, ln in enumerate(lines, 1):
        if "material_id" not in ln:
            raise ValueError(f"Dòng {idx}: thiếu material_id.")
        try:
            material_id = int(ln["material_id"])
        except Exception:
            raise ValueError(f"Dòng {idx}: material_id không hợp lệ.")
        try:
            qty = float(ln.get("qty", 0) or 0)
        except Exception:
            raise ValueError(f"Dòng {idx}: qty không hợp lệ.")
        if qty <= 0:
            raise ValueError(f"Dòng {idx}: qty phải > 0.")
        out.append({"material_id": material_id, "qty": qty})
    return out


# -------- APIs --------
def build_lines_from_pr(pr_id: int) -> List[Dict]:
    """Chuẩn bị lines cho RFQ dựa trên PR."""
    return pr_dao.get_pr_lines_as_dicts(pr_id)


def get_rfq_lines_as_dicts(rfq_id: int) -> List[Dict]:
    """Trả về list dict [{'material_id':..,'qty':..}] từ RFQ."""
    lines: List[RFQLine] = RFQLine.query.filter_by(rfq_id=rfq_id).all()
    return [{"material_id": int(l.material_id), "qty": float(l.qty)} for l in lines]


def create_rfq_from_pr(pr_id: int, status: str = "draft") -> RFQ:
    """Tạo RFQ và copy toàn bộ dòng từ PR. PR phải APPROVED."""
    _require_approved_pr(pr_id)  # <-- bắt PR APPROVED
    lines = build_lines_from_pr(pr_id)
    return create_rfq(pr_id=pr_id, status=status, lines=lines)


def list_rfqs() -> List[RFQ]:
    return RFQ.query.order_by(RFQ.id.desc()).all()


def get_rfq(rfq_id: int) -> Optional[RFQ]:
    return RFQ.query.get(rfq_id)


def create_rfq(pr_id: int | None, status: str, lines: List[Dict]) -> RFQ:
    """PR bắt buộc và phải APPROVED. Validate lines."""
    _require_approved_pr(pr_id)  # <-- bắt PR APPROVED
    norm_lines = _normalize_lines(lines)

    r = RFQ(
        pr_id=int(pr_id),
        status=_to_rfq_status(status),
    )
    db.session.add(r)
    db.session.flush()  # có r.id để insert RFQLine

    for ln in norm_lines:
        db.session.add(
            RFQLine(rfq_id=r.id, material_id=ln["material_id"], qty=ln["qty"])
        )
    _commit()
    return r


def update_rfq(rfq_id: int, pr_id: int | None, status: str, lines: List[Dict]) -> RFQ:
    """Nếu đổi/gán PR → PR phải APPROVED. RFQ đã APPROVED thì không cho đổi trạng thái/lines/PR."""
    r = RFQ.query.get_or_404(rfq_id)
    old_status = r.status
    new_status = _to_rfq_status(status)

    # Nếu RFQ đã APPROVED → cấm chỉnh sửa
    if old_status == RFQStatus.APPROVED:
        if new_status != RFQStatus.APPROVED:
            raise ValueError("RFQ đã APPROVED, không thể đổi sang trạng thái khác.")
        raise ValueError("RFQ đã APPROVED, không thể chỉnh sửa.")

    # Nếu có yêu cầu gán/đổi PR → PR phải APPROVED
    if pr_id is None:
        raise ValueError("Vui lòng chọn Purchase Requisition (PR).")
    _require_approved_pr(pr_id)
    r.pr_id = int(pr_id)
    r.status = new_status

    # replace toàn bộ lines (đã validate)
    norm_lines = _normalize_lines(lines)
    RFQLine.query.filter_by(rfq_id=r.id).delete()
    for ln in norm_lines:
        db.session.add(
            RFQLine(rfq_id=r.id, material_id=ln["material_id"], qty=ln["qty"])
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
