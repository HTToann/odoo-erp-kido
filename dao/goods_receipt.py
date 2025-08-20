# dao/goods_receipt.py
from typing import List, Dict, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from configs import db
from db.models.goods_receipt import GoodsReceipt, GRLine, GRStatus
from db.models.purchase import PurchaseOrder, POStatus, PurchaseOrderItem
from db.models.inventory import (
    StockMovement,
)  # nếu bạn đặt trong db/models/inventory.py
from dao import inventory as inv_dao


def _to_gr_status(v: str) -> GRStatus:
    m = {
        "draft": GRStatus.DRAFT,
        "checked": GRStatus.CHECKED,
        "posted": GRStatus.POSTED,
    }
    return m.get((v or "").strip().lower(), GRStatus.DRAFT)


def list_grs():
    return GoodsReceipt.query.order_by(GoodsReceipt.id.desc()).all()


def get_gr(gr_id: int) -> Optional[GoodsReceipt]:
    return GoodsReceipt.query.get(gr_id)


def create_gr(po_id: int, status: str, lines: List[Dict]) -> GoodsReceipt:
    po: PurchaseOrder = PurchaseOrder.query.get_or_404(int(po_id))
    if po.status != POStatus.CONFIRMED:
        raise ValueError("PO chưa CONFIRMED, không thể tạo GR.")

    # map còn lại theo po_line_id
    remaining_map = {ln["po_line_id"]: ln for ln in _remaining_for_po(po.id)}

    gr = GoodsReceipt(po_id=po.id, status=_to_gr_status(status))
    db.session.add(gr)
    db.session.flush()

    for ln in lines or []:
        mat_id = int(ln["material_id"])
        qty = float(ln["qty"] or 0)
        po_line_id = ln.get("po_line_id")  # NẾU form gửi kèm, sẽ check chặt hơn
        if qty <= 0:
            continue

        # Nếu biết po_line_id → chặn quá remaining
        if po_line_id:
            po_line_id = int(po_line_id)
            rem = remaining_map.get(po_line_id, {"remaining": 0})["remaining"]
            if qty > rem + 1e-9:
                raise ValueError(f"Nhận quá số còn lại (po_line #{po_line_id}).")

        db.session.add(
            GRLine(gr_id=gr.id, material_id=mat_id, qty=qty, po_line_id=po_line_id)
        )

    _after_save_status(gr)  # ghi kho nếu POSTED
    _commit()
    return gr


def update_gr(gr_id: int, po_id: int, status: str, lines: List[Dict]) -> GoodsReceipt:
    gr = GoodsReceipt.query.get_or_404(gr_id)
    po = PurchaseOrder.query.get_or_404(int(po_id))
    if po.status != POStatus.CONFIRMED:
        raise ValueError("PO chưa CONFIRMED, không thể cập nhật GR.")

    old_status = gr.status
    new_status = _to_gr_status(status)

    # ❌ Không cho hạ trạng thái từ POSTED xuống DRAFT/CHECKED
    if old_status == GRStatus.POSTED and new_status != GRStatus.POSTED:
        raise ValueError("GR đã POSTED, không được chuyển về DRAFT/CHECKED.")

    gr.po_id = po.id
    gr.status = new_status

    # thay toàn bộ lines
    GRLine.query.filter_by(gr_id=gr.id).delete()

    remaining_map = {
        ln["po_line_id"]: ln for ln in _remaining_for_po(po.id, exclude_gr_id=gr.id)
    }
    for ln in lines or []:
        mat_id = int(ln["material_id"])
        qty = float(ln["qty"] or 0)
        po_line_id = ln.get("po_line_id")
        if qty <= 0:
            continue
        if po_line_id:
            po_line_id = int(po_line_id)
            rem = remaining_map.get(po_line_id, {"remaining": 0})["remaining"]
            if qty > rem + 1e-9:
                raise ValueError(f"Nhận quá số còn lại (po_line #{po_line_id}).")
        db.session.add(
            GRLine(gr_id=gr.id, material_id=mat_id, qty=qty, po_line_id=po_line_id)
        )

    _after_save_status(gr)  # đã xử lý movement/stock phù hợp với status
    _commit()
    return gr


def delete_gr(gr_id: int):
    gr = GoodsReceipt.query.get_or_404(gr_id)
    # Nếu trước đây có ghi GRN thì rollback (an toàn)
    inv_dao.remove_movements(ref_type="GRN", ref_id=gr.id)
    db.session.delete(gr)
    _commit()


# ---------- helpers ----------
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
            "material_id": r.material_id,
            "ordered": float(r.ordered or 0),
            "received": 0.0,
            "remaining": float(r.ordered or 0),
        }
        for r in q.filter(PurchaseOrderItem.po_id == po_id)
    }

    # cộng nhận
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
            lines[po_line_id]["received"] = float(sqty or 0)
            lines[po_line_id]["remaining"] = max(
                0.0, lines[po_line_id]["ordered"] - lines[po_line_id]["received"]
            )
    return list(lines.values())


def _after_save_status(gr: GoodsReceipt):
    return
    # """
    # Quy tắc:
    # - Xóa movement cũ của GR (nếu có) và rollback tồn (inv_dao.remove_movements)
    # - Nếu status == POSTED → ghi lại movement mới cho từng dòng và cộng tồn
    # """
    # # 1) rollback tất cả movement cũ của GR
    # inv_dao.remove_movements(ref_type="GRN", ref_id=gr.id)

    # # 2) nếu đang POSTED → ghi movement mới & cộng tồn
    # if gr.status == GRStatus.POSTED:
    #     for ln in gr.lines:
    #         inv_dao.add_movement(
    #             material_id=int(ln.material_id),
    #             ref_type="GRN",
    #             ref_id=gr.id,
    #             qty_change=ln.qty,  # số dương để nhập kho
    #         )


def delete_gr(gr_id: int):
    gr = GoodsReceipt.query.get_or_404(gr_id)

    # Nếu đã POSTED → rollback tồn trước khi xóa
    if gr.status == GRStatus.POSTED:
        inv_dao.remove_movements(ref_type="GRN", ref_id=gr.id)

    db.session.delete(gr)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
