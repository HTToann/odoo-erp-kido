# dao/qc.py
from datetime import datetime, timezone
from typing import List, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from configs import db

from db.models.qc import QCReport as QC, QCLine, QCStatus
from db.models.goods_receipt import GoodsReceipt, GRLine as GoodsReceiptLine
from db.models.inventory import StockMovement
from db.models.material import Material
from dao import inventory as inv_dao


# ---------- helpers ----------
def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


_QC_FORM_TO_ENUM = {
    "pending": QCStatus.PENDING,
    "passed": QCStatus.PASSED,
    "failed": QCStatus.FAILED,
}


def _to_qc_status(value: Optional[str]) -> QCStatus:
    if not value:
        return QCStatus.PENDING
    return _QC_FORM_TO_ENUM.get((value or "").strip().lower(), QCStatus.PENDING)


def _has_accepted_qty() -> bool:
    # Cho phép code chạy an toàn cả khi bạn CHƯA thêm cột accepted_qty
    return hasattr(QCLine, "accepted_qty")


# =========================
#          Queries
# =========================
def list_qcs() -> List[QC]:
    return (
        QC.query.options(
            joinedload(QC.lines)
            .joinedload(QCLine.gr_line)
            .joinedload(GoodsReceiptLine.material),
            joinedload(QC.lines)
            .joinedload(QCLine.gr_line)
            .joinedload(GoodsReceiptLine.gr),
        )
        .order_by(QC.id.desc())
        .all()
    )


def get_qc(qc_id: int) -> Optional[QC]:
    return QC.query.options(
        joinedload(QC.lines)
        .joinedload(QCLine.gr_line)
        .joinedload(GoodsReceiptLine.material),
        joinedload(QC.lines).joinedload(QCLine.gr_line).joinedload(GoodsReceiptLine.gr),
    ).get(qc_id)


def list_all_gr_lines() -> List[GoodsReceiptLine]:
    return (
        GoodsReceiptLine.query.options(
            joinedload(GoodsReceiptLine.material),
            joinedload(GoodsReceiptLine.gr),
        )
        .order_by(GoodsReceiptLine.id.desc())
        .all()
    )


# =========================
#         Mutations
# =========================
def create_qc(gr_id: Optional[int], status: str, lines: List[Dict]) -> QC:
    gr = _require_posted_gr(gr_id)  # <-- BẮT BUỘC GR.POSTED

    if not lines:
        raise ValueError("Vui lòng nhập ít nhất 1 dòng QC.")

    qc = QC(
        gr_id=gr.id,
        status=_to_qc_status(status),
    )
    db.session.add(qc)
    db.session.flush()

    seen = set()
    for idx, ln in enumerate(lines, 1):
        gr_line_id = ln.get("gr_line_id")
        if not gr_line_id:
            raise ValueError(f"Dòng {idx}: thiếu gr_line_id.")
        gr_line_id = int(gr_line_id)

        if gr_line_id in seen:
            raise ValueError(f"Dòng {idx}: gr_line_id bị trùng trong phiếu QC.")
        seen.add(gr_line_id)

        gr_line = GoodsReceiptLine.query.get_or_404(gr_line_id)
        if gr_line.gr_id != gr.id:
            raise ValueError(
                f"Dòng {idx}: GR line #{gr_line_id} không thuộc GR #{gr.id}."
            )

        result = _coerce_result(ln.get("result"))
        note = ln.get("note")

        qc_line = QCLine(qc=qc, gr_line_id=gr_line_id, result=result, note=note)

        if _has_accepted_qty():
            gr_qty = float(gr_line.qty or 0)
            if result == "pass":
                acc = ln.get("accepted_qty")
                acc = float(acc) if acc is not None else gr_qty
            else:
                acc = float(ln.get("accepted_qty") or 0)
                if acc > 0:
                    raise ValueError(
                        f"Dòng {idx}: kết quả FAIL thì accepted_qty phải = 0."
                    )

            if acc < 0 or acc > gr_qty + 1e-9:
                raise ValueError(
                    f"Dòng {idx}: accepted_qty vượt quá số nhận của GR line #{gr_line.id}."
                )
            qc_line.accepted_qty = acc

        db.session.add(qc_line)

    _commit()
    return qc


def _save_qc_lines(qc: "QC", lines: List[Dict]) -> None:
    if not qc.gr_id:
        raise ValueError("QC chưa gắn với GR, không thể ghi dòng.")

    gr = _require_posted_gr(qc.gr_id)  # đảm bảo GR.POSTED

    QCLine.query.filter_by(qc_id=qc.id).delete()
    db.session.flush()

    seen = set()
    for idx, ln in enumerate(lines or [], 1):
        gr_line_id = ln.get("gr_line_id")
        if not gr_line_id:
            raise ValueError(f"Dòng {idx}: thiếu gr_line_id.")
        gr_line_id = int(gr_line_id)

        if gr_line_id in seen:
            raise ValueError(f"Dòng {idx}: gr_line_id bị trùng trong phiếu QC.")
        seen.add(gr_line_id)

        gr_line = GoodsReceiptLine.query.get_or_404(gr_line_id)
        if gr_line.gr_id != gr.id:
            raise ValueError(
                f"Dòng {idx}: GR line #{gr_line_id} không thuộc GR #{gr.id}."
            )

        result = _coerce_result(ln.get("result"))
        note = ln.get("note")

        qcl = QCLine(qc=qc, gr_line_id=gr_line_id, result=result, note=note)

        if _has_accepted_qty():
            gr_qty = float(gr_line.qty or 0)
            if result == "pass":
                acc = ln.get("accepted_qty")
                acc = float(acc) if acc is not None else gr_qty
            else:
                acc = float(ln.get("accepted_qty") or 0)
                if acc > 0:
                    raise ValueError(
                        f"Dòng {idx}: kết quả FAIL thì accepted_qty phải = 0."
                    )

            if acc < 0 or acc > gr_qty + 1e-9:
                raise ValueError(
                    f"Dòng {idx}: accepted_qty vượt quá số nhận của GR line #{gr_line.id}."
                )
            qcl.accepted_qty = acc

        db.session.add(qcl)

    db.session.flush()


def _set_checked_at(old_status: "QCStatus", new_status: "QCStatus", qc: "QC") -> None:
    """Chỉ set timestamp khi lần đầu rời PENDING -> PASSED/FAILED; reset khi quay lại PENDING."""
    if old_status == QCStatus.PENDING and new_status in (
        QCStatus.PASSED,
        QCStatus.FAILED,
    ):
        qc.checked_at = datetime.now(timezone.utc)
    elif new_status == QCStatus.PENDING:
        qc.checked_at = None
    # các trường hợp còn lại: giữ nguyên qc.checked_at


# -----------------------------
# Update (không ghi kho)
# -----------------------------
def update_qc(
    qc_id: int, gr_id: Optional[int], status: str, lines: List[Dict]
) -> Optional["QC"]:
    qc = get_qc(qc_id)
    if not qc:
        return None

    old_status = qc.status
    old_gr_id = qc.gr_id
    new_status = _to_qc_status(status)

    # đã PASSED -> không đổi trạng thái & không đổi GR
    if old_status == QCStatus.PASSED and new_status != QCStatus.PASSED:
        raise ValueError("QC đã PASSED, không thể đổi sang trạng thái khác.")
    if old_status == QCStatus.PASSED and gr_id and int(gr_id) != old_gr_id:
        raise ValueError("QC đã PASSED, không được đổi GR.")

    # nếu có yêu cầu đổi/gán GR -> GR phải POSTED
    if gr_id is not None:
        gr = _require_posted_gr(gr_id)
        qc.gr_id = gr.id

    qc.status = new_status
    _set_checked_at(old_status, new_status, qc)

    _save_qc_lines(qc, lines)
    _commit()
    return qc


# -----------------------------
# Finalize (ghi kho phần đạt)
# -----------------------------
def finalize_qc(qc_id: int, status: str, lines: List[Dict]) -> QC:
    qc = get_qc(qc_id)
    if not qc:
        raise ValueError("QC không tồn tại.")

    # QC phải có GR và GR.POSTED
    _require_posted_gr(qc.gr_id)

    old_status = qc.status
    new_status = _to_qc_status(status)
    if new_status == QCStatus.PENDING:
        raise ValueError("Không thể chốt QC về trạng thái PENDING.")
    if old_status == QCStatus.PASSED and new_status != QCStatus.PASSED:
        raise ValueError("QC đã PASSED, không thể đổi sang trạng thái khác.")

    _save_qc_lines(qc, lines)

    _set_checked_at(old_status, new_status, qc)
    qc.status = new_status
    db.session.flush()

    if qc.status == QCStatus.PASSED:
        inv_dao.remove_movements("QC_PASS", qc.id)

        db.session.expire(qc, ["lines"])
        fresh_lines = qc.lines

        affected = set()
        for ln in fresh_lines:
            if _has_accepted_qty():
                qty_in = float(ln.accepted_qty or 0)
            else:
                gr_line = GoodsReceiptLine.query.get(ln.gr_line_id)
                qty_in = float(gr_line.qty or 0) if ln.result == "pass" else 0.0

            if qty_in > 0:
                inv_dao.add_movement(
                    material_id=ln.gr_line.material_id,
                    ref_type="QC_PASS",
                    ref_id=qc.id,
                    qty_change=qty_in,
                )
                affected.add(ln.gr_line.material_id)

        if affected:
            inv_dao.sync_stock_items(affected)

    _commit()
    return qc


def delete_qc(qc_id: int) -> bool:
    qc = get_qc(qc_id)
    if not qc:
        return False

    # Không cho xoá nếu đã PASSED (tránh 'lùi' kho)
    if qc.status == QCStatus.PASSED:
        raise ValueError("QC đã PASSED, không thể xoá.")

    db.session.delete(qc)
    _commit()
    return True


# ---------- helpers thêm ----------
def _require_posted_gr(gr_id: int) -> GoodsReceipt:
    """Lấy GR và đảm bảo GR.POSTED, nếu không thì raise ValueError/404 hợp lý."""
    if not gr_id:
        raise ValueError("Vui lòng chọn phiếu GR.")
    gr = GoodsReceipt.query.get_or_404(int(gr_id))
    from db.models.goods_receipt import GRStatus  # tránh vòng import

    if gr.status != GRStatus.POSTED:
        raise ValueError("Chỉ được tạo/ghi QC khi GR đã POSTED.")
    return gr


def _coerce_result(v: Optional[str]) -> str:
    s = (v or "").strip().lower()
    if s in ("pass", "fail"):
        return s
    # ép giá trị lạ về 'fail' để an toàn, hoặc raise nếu muốn cứng
    return "fail"
