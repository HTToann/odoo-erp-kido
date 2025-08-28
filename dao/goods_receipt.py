# dao/goods_receipt.py
from typing import List, Dict, Optional
from collections import defaultdict
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from configs import db
from db.models.goods_receipt import GoodsReceipt, GRLine, GRStatus
from db.models.purchase import PurchaseOrder, POStatus, PurchaseOrderItem
from dao import inventory as inv_dao

EPS = 1e-9  # dung sai so hoc


# ---------- status helpers ----------
def _to_gr_status(v: str) -> GRStatus:
    s = (v or "").strip().lower()
    if s == "draft":
        return GRStatus.DRAFT
    if s == "checked":
        return GRStatus.CHECKED
    if s == "posted":
        return GRStatus.POSTED
    return GRStatus.DRAFT


# ---------- public APIs ----------
def list_grs():
    return GoodsReceipt.query.order_by(GoodsReceipt.id.desc()).all()


def get_gr(gr_id: int) -> Optional[GoodsReceipt]:
    return GoodsReceipt.query.get(gr_id)


def create_gr(po_id: int, status: str, lines: List[Dict]) -> GoodsReceipt:
    po: PurchaseOrder = PurchaseOrder.query.get_or_404(int(po_id))
    if po.status != POStatus.CONFIRMED:
        raise ValueError("PO chưa CONFIRMED, không thể tạo GR.")

    if not lines:
        raise ValueError("Vui lòng nhập ít nhất 1 dòng.")

    # remaining theo từng po_line
    remaining_map = {ln["po_line_id"]: ln for ln in _remaining_for_po(po.id)}

    # build map các po_line của PO
    po_lines = _po_lines_of_po(po.id)

    # Chuẩn hóa / validate lines, resolve po_line_id nếu thiếu
    norm_lines = _normalize_and_validate_lines(lines, po_lines, remaining_map)

    gr = GoodsReceipt(po_id=po.id, status=_to_gr_status(status))
    db.session.add(gr)
    db.session.flush()  # cần gr.id

    for ln in norm_lines:
        db.session.add(
            GRLine(
                gr_id=gr.id,
                material_id=ln["material_id"],
                qty=ln["qty"],
                po_line_id=ln["po_line_id"],
            )
        )

    _after_save_status(gr)  # ghi/rollback kho theo status
    _commit()
    return gr


def update_gr(gr_id: int, po_id: int, status: str, lines: List[Dict]) -> GoodsReceipt:
    gr = GoodsReceipt.query.get_or_404(gr_id)
    po = PurchaseOrder.query.get_or_404(int(po_id))

    if po.status != POStatus.CONFIRMED:
        raise ValueError("PO chưa CONFIRMED, không thể cập nhật GR.")

    # Không cho đổi PO sau khi GR đã tạo (tránh rối định danh movement)
    if gr.po_id != po.id:
        raise ValueError("Không được đổi PO của phiếu GR.")

    old_status = gr.status
    new_status = _to_gr_status(status)

    # Đã POSTED thì không cho chỉnh gì nữa
    if old_status == GRStatus.POSTED:
        if new_status != GRStatus.POSTED:
            raise ValueError("GR đã POSTED, không được chuyển về DRAFT/CHECKED.")
        # dù cố giữ POSTED -> cũng không cho sửa line
        raise ValueError("GR đã POSTED, không thể chỉnh sửa.")

    if not lines:
        raise ValueError("Vui lòng nhập ít nhất 1 dòng.")

    # Tính remaining ngoại trừ chính GR này
    remaining_map = {
        ln["po_line_id"]: ln for ln in _remaining_for_po(po.id, exclude_gr_id=gr.id)
    }
    po_lines = _po_lines_of_po(po.id)
    norm_lines = _normalize_and_validate_lines(lines, po_lines, remaining_map)

    gr.status = new_status

    # thay toàn bộ lines
    GRLine.query.filter_by(gr_id=gr.id).delete()
    for ln in norm_lines:
        db.session.add(
            GRLine(
                gr_id=gr.id,
                material_id=ln["material_id"],
                qty=ln["qty"],
                po_line_id=ln["po_line_id"],
            )
        )

    _after_save_status(gr)
    _commit()
    return gr


def delete_gr(gr_id: int):
    gr = GoodsReceipt.query.get_or_404(gr_id)
    # rollback movement cũ nếu có
    inv_dao.remove_movements(ref_type="GRN", ref_id=gr.id)
    db.session.delete(gr)
    _commit()


# ---------- helpers ----------
def _po_lines_of_po(po_id: int) -> Dict[int, dict]:
    """Trả map {po_line_id: {material_id, ordered}} cho PO."""
    rows = (
        db.session.query(
            PurchaseOrderItem.id.label("po_line_id"),
            PurchaseOrderItem.material_id,
            PurchaseOrderItem.qty.label("ordered"),
        )
        .filter(PurchaseOrderItem.po_id == po_id)
        .all()
    )
    return {
        r.po_line_id: {
            "material_id": int(r.material_id),
            "ordered": float(r.ordered or 0.0),
        }
        for r in rows
    }


def _remaining_for_po(po_id: int, exclude_gr_id: int | None = None):
    """Tính remaining cho từng po_line; có thể loại trừ 1 GR khi edit."""
    q = db.session.query(
        PurchaseOrderItem.id.label("po_line_id"),
        PurchaseOrderItem.material_id,
        PurchaseOrderItem.qty.label("ordered"),
    )
    lines = {
        r.po_line_id: {
            "po_line_id": r.po_line_id,
            "material_id": int(r.material_id),
            "ordered": float(r.ordered or 0.0),
            "received": 0.0,
            "remaining": float(r.ordered or 0.0),
        }
        for r in q.filter(PurchaseOrderItem.po_id == po_id)
    }

    gq = (
        db.session.query(GRLine.po_line_id, func.sum(GRLine.qty))
        .join(GoodsReceipt, GoodsReceipt.id == GRLine.gr_id)
        .filter(
            GoodsReceipt.po_id == po_id,
            GoodsReceipt.status.in_([GRStatus.CHECKED, GRStatus.POSTED]),
        )
    )
    if exclude_gr_id:
        gq = gq.filter(GoodsReceipt.id != exclude_gr_id)
    gq = gq.group_by(GRLine.po_line_id).all()

    for po_line_id, sqty in gq:
        if po_line_id in lines:
            received = float(sqty or 0.0)
            lines[po_line_id]["received"] = received
            lines[po_line_id]["remaining"] = max(
                0.0, lines[po_line_id]["ordered"] - received
            )

    return list(lines.values())


def _normalize_and_validate_lines(
    lines: List[Dict], po_lines: Dict[int, dict], remaining_map: Dict[int, dict]
) -> List[Dict]:
    """
    - Chuẩn hóa qty/material_id về số
    - Resolve po_line_id nếu không gửi
    - Check over-receipt theo từng po_line
    - Check material khớp với po_line
    """
    if not po_lines:
        raise ValueError("PO không có dòng nào, không thể tạo GR.")

    # Build index theo material -> list po_line_id
    mat_to_po_lines = defaultdict(list)
    for pl_id, pl in po_lines.items():
        mat_to_po_lines[pl["material_id"]].append(pl_id)

    # Gộp qty theo po_line sau khi resolve, để check tổng <= remaining
    sum_by_po_line: Dict[int, float] = defaultdict(float)

    normalized: List[Dict] = []
    for idx, ln in enumerate(lines, 1):
        try:
            material_id = int(ln["material_id"])
        except Exception:
            raise ValueError(f"Dòng {idx}: thiếu hoặc sai material_id.")
        qty = float(ln.get("qty", 0) or 0)
        if qty <= EPS:
            raise ValueError(f"Dòng {idx}: số lượng phải > 0.")

        po_line_id = ln.get("po_line_id")
        if po_line_id:
            po_line_id = int(po_line_id)
            if po_line_id not in po_lines:
                raise ValueError(f"Dòng {idx}: po_line_id không thuộc PO.")
            # check material khớp
            if po_lines[po_line_id]["material_id"] != material_id:
                raise ValueError(
                    f"Dòng {idx}: vật tư không khớp với PO line #{po_line_id}."
                )
        else:
            # resolve theo material_id -> phải duy nhất
            candidates = mat_to_po_lines.get(material_id, [])
            if not candidates:
                raise ValueError(f"Dòng {idx}: vật tư không tồn tại trong PO.")
            if len(candidates) > 1:
                raise ValueError(
                    f"Dòng {idx}: vật tư xuất hiện ở nhiều PO line, vui lòng chọn po_line_id."
                )
            po_line_id = candidates[0]

        normalized.append(
            {"material_id": material_id, "qty": qty, "po_line_id": po_line_id}
        )
        sum_by_po_line[po_line_id] += qty

    # Check tổng theo po_line không vượt remaining
    for po_line_id, total_qty in sum_by_po_line.items():
        remaining = float(
            remaining_map.get(po_line_id, {"remaining": 0.0})["remaining"]
        )
        if total_qty > remaining + EPS:
            raise ValueError(f"Nhận quá số còn lại (PO line #{po_line_id}).")

    return normalized


def _after_save_status(gr: GoodsReceipt):
    # """
    # - Luôn rollback movement cũ của GR
    # - Nếu status == POSTED -> ghi lại movement nhập kho cho từng dòng
    # """
    # # rollback tất cả movement cũ của GR
    # inv_dao.remove_movements(ref_type="GRN", ref_id=gr.id)

    # # nếu đang POSTED → ghi movement mới & cộng tồn
    # if gr.status == GRStatus.POSTED:
    #     for ln in gr.lines:
    #         inv_dao.add_movement(
    #             material_id=int(ln.material_id),
    #             ref_type="GRN",
    #             ref_id=gr.id,
    #             qty_change=float(ln.qty),  # số dương để nhập kho
    #         )
    return


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
