# dao/purchase_return.py
from typing import Optional, List, Dict, Iterable
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from configs import db
from db.models.purchase_return import PurchaseReturn, ReturnLine, PurchaseReturnStatus
from db.models.goods_receipt import GRLine, GoodsReceipt
from db.models.inventory import StockMovement
from dao import inventory as inv_dao

# Map từ form string -> Enum
_RET_FORM_TO_ENUM = {
    "draft": PurchaseReturnStatus.DRAFT,
    "approved": PurchaseReturnStatus.APPROVED,
    "returned": PurchaseReturnStatus.RETURNED,
    "posted": PurchaseReturnStatus.POSTED,
}


def _assert_lines_belong_to_gr(gr_id: int, lines: List[Dict]):
    valid_ids = {
        gid
        for (gid,) in db.session.query(GRLine.id)
        .join(GoodsReceipt)
        .filter(GoodsReceipt.id == int(gr_id))
        .all()
    }
    for idx, ln in enumerate(lines or [], 1):
        gid = int(ln["gr_line_id"])
        if gid not in valid_ids:
            raise ValueError(f"Dòng {idx}: GR line #{gid} không thuộc GR #{gr_id}.")


def _to_ret_status(value: str | None) -> PurchaseReturnStatus:
    if not value:
        return PurchaseReturnStatus.DRAFT
    return _RET_FORM_TO_ENUM.get(
        (value or "").strip().lower(), PurchaseReturnStatus.DRAFT
    )


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


# ----- helper: qty đã nhập kho theo QC_PASS cho từng GR line -----
def _accepted_qty_map_for_gr(gr_id: int) -> dict[int, float]:
    """
    Tổng qty đã nhập kho từ QC_PASS theo từng GR line.
    Tính từ StockMovement(ref_type='QC_PASS', +qty).
    """
    rows = (
        db.session.query(
            StockMovement.ref_id,
            StockMovement.material_id,
            func.sum(StockMovement.qty_change),
        )
        .filter(StockMovement.ref_type == "QC_PASS")
        .group_by(StockMovement.ref_id, StockMovement.material_id)
        .all()
    )
    # ref_id ở đây là qc_id; cần map về gr_line? -> ta suy luận qua QCLine đã được dùng khi post
    # Đơn giản hơn: dựa trực tiếp trên bảng QCLine nếu bạn có accepted_qty; nhưng để độc lập, ta tính “được trả tối đa”
    # theo từng gr_line bằng:
    #   accepted_qty(gr_line) = SUM(QC_PASS movements của chính material và thuộc GR có line này)
    # Vì movement không lưu gr_line_id, ta quay về cách trực tiếp:
    #   Lấy accepted_qty từ QCLine nếu có cột accepted_qty. Nếu không có, coi PASS = full gr_line.qty.
    from db.models.qc import QCLine, QCReport, QCStatus

    q = (
        db.session.query(QCLine.gr_line_id, func.sum(QCLine.accepted_qty))
        .join(QCReport, QCReport.id == QCLine.qc_id)
        .join(GRLine, GRLine.id == QCLine.gr_line_id)
        .filter(QCReport.status == QCStatus.PASSED, GRLine.gr_id == gr_id)
        .group_by(QCLine.gr_line_id)
    )
    acc = {gid: float(t or 0) for gid, t in q.all()}
    # Nếu chưa có cột accepted_qty, fallback PASS = full line.qty
    if not hasattr(QCLine, "accepted_qty"):
        q2 = (
            db.session.query(QCLine.gr_line_id, func.sum(GRLine.qty))
            .join(QCReport, QCReport.id == QCLine.qc_id)
            .join(GRLine, GRLine.id == QCLine.gr_line_id)
            .filter(
                QCReport.status == QCStatus.PASSED,
                GRLine.gr_id == gr_id,
                func.lower(QCLine.result) == "pass",
            )
            .group_by(QCLine.gr_line_id)
        )
        for gid, t in q2.all():
            acc[gid] = float(t or 0)
    return acc


# ----- helper: qty đã POSTED trả về NCC theo từng GR line -----
def _returned_qty_map_for_gr(
    gr_id: int, exclude_return_id: int | None = None
) -> dict[int, float]:
    q = (
        db.session.query(ReturnLine.gr_line_id, func.sum(ReturnLine.qty))
        .join(PurchaseReturn, PurchaseReturn.id == ReturnLine.return_id)
        .filter(
            PurchaseReturn.gr_id == gr_id,
            PurchaseReturn.status == PurchaseReturnStatus.POSTED,
        )
    )
    if exclude_return_id:
        q = q.filter(PurchaseReturn.id != exclude_return_id)
    q = q.group_by(ReturnLine.gr_line_id).all()
    return {gid: float(t or 0) for gid, t in q}


# API nội bộ: số còn có thể trả cho từng gr_line
def remaining_to_return_by_gr(
    gr_id: int, exclude_return_id: int | None = None
) -> dict[int, float]:
    acc = _accepted_qty_map_for_gr(gr_id)
    ret = _returned_qty_map_for_gr(gr_id, exclude_return_id=exclude_return_id)
    remain = {}
    for gid, a in acc.items():
        r = ret.get(gid, 0.0)
        remain[gid] = max(0.0, a - r)
    return remain


# ========================= CRUD =========================
def list_returns() -> List[PurchaseReturn]:
    return PurchaseReturn.query.order_by(PurchaseReturn.id.desc()).all()


def get_return(return_id: int) -> Optional[PurchaseReturn]:
    return PurchaseReturn.query.get(return_id)


def create_return(gr_id: int, status: str, lines: List[Dict]) -> PurchaseReturn:
    r = PurchaseReturn(gr_id=int(gr_id), status=_to_ret_status(status))
    db.session.add(r)
    db.session.flush()

    _assert_lines_belong_to_gr(gr_id=int(gr_id), lines=lines)
    _validate_lines_against_remaining(
        gr_id=int(gr_id), lines=lines, exclude_return_id=None
    )

    for ln in lines or []:
        db.session.add(
            ReturnLine(
                return_id=r.id,
                gr_line_id=int(ln["gr_line_id"]),
                qty=float(ln["qty"] or 0),
                reason=ln.get("reason"),
            )
        )
    _post_if_needed(r)
    _commit()
    return r


def update_return(
    return_id: int, gr_id: int, status: str, lines: List[Dict]
) -> PurchaseReturn:
    r = PurchaseReturn.query.get_or_404(return_id)
    old_status = r.status
    new_status = _to_ret_status(status)

    if (
        old_status == PurchaseReturnStatus.POSTED
        and new_status != PurchaseReturnStatus.POSTED
    ):
        raise ValueError("Phiếu trả hàng đã POSTED, không thể đổi trạng thái khác.")
    if old_status == PurchaseReturnStatus.POSTED and int(gr_id) != r.gr_id:
        raise ValueError("Phiếu trả hàng đã POSTED, không được đổi GR.")

    r.gr_id = int(gr_id)
    r.status = new_status

    ReturnLine.query.filter_by(return_id=r.id).delete()
    db.session.flush()

    _assert_lines_belong_to_gr(gr_id=r.gr_id, lines=lines)
    _validate_lines_against_remaining(
        gr_id=r.gr_id, lines=lines, exclude_return_id=r.id
    )

    for ln in lines or []:
        db.session.add(
            ReturnLine(
                return_id=r.id,
                gr_line_id=int(ln["gr_line_id"]),
                qty=float(ln["qty"] or 0),
                reason=ln.get("reason"),
            )
        )

    _post_if_needed(r)
    _commit()
    return r


def delete_return(return_id: int) -> None:
    r = PurchaseReturn.query.get_or_404(return_id)
    # rollback movement nếu đã POSTED
    if r.status == PurchaseReturnStatus.POSTED:
        inv_dao.remove_movements("RETURN", r.id)
    db.session.delete(r)
    _commit()


# ========================= Posting =========================
def _post_if_needed(r: PurchaseReturn) -> None:
    """
    Nếu status == POSTED:
      - Xóa movement RETURN cũ (rollback tồn) rồi ghi lại theo lines hiện tại (qty âm).
    Nếu status != POSTED:
      - Đảm bảo không còn movement RETURN cho chứng từ này.
    """
    inv_dao.remove_movements("RETURN", r.id)

    if r.status == PurchaseReturnStatus.POSTED:
        affected: set[int] = set()
        for ln in r.lines or []:
            qty = float(ln.qty or 0)
            if qty <= 0:
                continue
            # movement âm để trừ kho
            inv_dao.add_movement(
                material_id=ln.gr_line.material_id,
                ref_type="RETURN",
                ref_id=r.id,
                qty_change=-qty,
            )
            affected.add(ln.gr_line.material_id)
        if affected:
            inv_dao.sync_stock_items(affected)


# ========================= Validate =========================
def _validate_lines_against_remaining(
    gr_id: int, lines: List[Dict], exclude_return_id: int | None
):
    remain = remaining_to_return_by_gr(gr_id, exclude_return_id=exclude_return_id)
    for ln in lines or []:
        gid = int(ln["gr_line_id"])
        qty = float(ln["qty"] or 0)
        if qty < 0:
            raise ValueError("Số lượng trả phải ≥ 0.")
        allow = remain.get(gid, 0.0)
        if qty > allow + 1e-9:
            raise ValueError(
                f"Số trả ({qty}) vượt quá số còn có thể trả ({allow}) của GR line #{gid}."
            )
