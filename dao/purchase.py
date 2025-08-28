# dao/purchase.py
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case
from configs import db
from db.models.purchase import PurchaseOrder, PurchaseOrderItem, POStatus
from db.models.goods_receipt import GoodsReceipt, GRLine, GRStatus
from db.models.vendor_quotation import (
    VendorQuotation,
    VendorQuotationStatus,
)


def _to_po_status(value: str) -> POStatus:
    if not value:
        return POStatus.DRAFT
    value = value.strip().upper()
    try:
        return POStatus[value]
    except KeyError:
        for s in POStatus:
            if s.value == value:
                return s
        return POStatus.DRAFT


def list_purchases() -> List[PurchaseOrder]:
    return PurchaseOrder.query.order_by(
        PurchaseOrder.order_date.desc().nullslast()
    ).all()


def list_purchases_confirmed() -> List[PurchaseOrder]:
    return (
        PurchaseOrder.query.filter(PurchaseOrder.status == POStatus.CONFIRMED)
        .order_by(PurchaseOrder.id.desc())
        .all()
    )


def po_lines_with_remaining(po_id: int) -> List[dict]:
    """
    Trả về list dict: {po_line_id, material_id, ordered, received, remaining}
    - received = tổng GRLine.qty của các GR có status CHECKED/POSTED
    """
    q = (
        db.session.query(
            PurchaseOrderItem.id.label("po_line_id"),
            PurchaseOrderItem.material_id,
            PurchaseOrderItem.qty.label("ordered"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            GoodsReceipt.status.in_(
                                [GRStatus.CHECKED, GRStatus.POSTED]
                            ),
                            GRLine.qty,
                        ),
                        else_=0.0,
                    )
                ),
                0.0,
            ).label("received"),
        )
        .select_from(PurchaseOrderItem)
        .outerjoin(GRLine, GRLine.po_line_id == PurchaseOrderItem.id)
        .outerjoin(GoodsReceipt, GoodsReceipt.id == GRLine.gr_id)
        .filter(PurchaseOrderItem.po_id == po_id)
        .group_by(PurchaseOrderItem.id)
    )

    rows = []
    for r in q:
        remaining = float((r.ordered or 0) - (r.received or 0))
        rows.append(
            {
                "po_line_id": r.po_line_id,
                "material_id": int(r.material_id),
                "ordered": float(r.ordered or 0),
                "received": float(r.received or 0),
                "remaining": max(0.0, remaining),
            }
        )
    return rows


def get_po(po_id: int) -> Optional[PurchaseOrder]:
    return PurchaseOrder.query.get(po_id)


# ---------------- helpers ----------------
def _require_selected_vq(vq_id: int) -> VendorQuotation:
    """Lấy VQ và đảm bảo VQ.SELECTED, nếu không raise lỗi."""
    if not vq_id:
        raise ValueError("Vui lòng chọn báo giá (VQ).")
    vq = VendorQuotation.query.get_or_404(int(vq_id))
    if vq.status != VendorQuotationStatus.SELECTED:
        raise ValueError("Chỉ có thể tạo/cập nhật PO khi VQ đã được SELECTED.")
    return vq


def _ensure_vq_not_used(vq_id: int, exclude_po_id: int | None = None) -> None:
    """
    Đảm bảo VQ chưa được gán cho PO nào khác (rule #1: one VQ -> one PO).
    exclude_po_id: bỏ qua PO hiện tại khi update.
    """
    qry = PurchaseOrder.query.filter(PurchaseOrder.vq_id == int(vq_id))
    if exclude_po_id:
        qry = qry.filter(PurchaseOrder.id != int(exclude_po_id))
    exists = db.session.query(qry.exists()).scalar()
    if exists:
        raise ValueError("VQ này đã được dùng để tạo PO khác.")


def _parse_date(s: str | None):
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d")


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


# ---------------- mutations ----------------
def create_po(
    po_no: str,
    supplier_id: int,
    status: str,
    order_date,
    expected_date,
    subtotal,
    tax,
    total,
    vq_id: int | None = None,
) -> PurchaseOrder:
    # Rule: bắt buộc VQ SELECTED + chưa bị dùng (rule #1)
    vq = _require_selected_vq(vq_id)
    _ensure_vq_not_used(vq.id)  # one VQ -> one PO

    # (khuyến nghị) nhà cung cấp phải trùng với VQ
    if vq.supplier_id and int(supplier_id) != int(vq.supplier_id):
        raise ValueError(
            "Nhà cung cấp của PO phải trùng với nhà cung cấp của VQ đã chọn."
        )

    po = PurchaseOrder(
        po_no=po_no.strip(),
        supplier_id=int(supplier_id),
        status=_to_po_status(status),
        order_date=_parse_date(order_date),
        expected_date=_parse_date(expected_date),
        subtotal=Decimal(str(subtotal or 0)),
        tax=Decimal(str(tax or 0)),
        total=Decimal(str(total or 0)),
        vq_id=int(vq.id),
    )
    db.session.add(po)
    _commit()
    return po


def update_po(
    po_id: int,
    po_no: str,
    supplier_id: int,
    status: str,
    order_date,
    expected_date,
    subtotal,
    tax,
    total,
    vq_id: int | None = None,
) -> PurchaseOrder:
    po = PurchaseOrder.query.get_or_404(po_id)

    # Rule #3: PO đã CONFIRMED -> không cho chỉnh sửa
    if po.status == POStatus.CONFIRMED:
        raise ValueError("PO đã CONFIRMED, không thể chỉnh sửa.")

    # Rule: nếu gán/đổi VQ -> VQ phải SELECTED và chưa bị dùng bởi PO khác (rule #1)
    vq = _require_selected_vq(vq_id)
    _ensure_vq_not_used(vq.id, exclude_po_id=po.id)

    # (khuyến nghị) nhà cung cấp phải trùng với VQ
    if vq.supplier_id and int(supplier_id) != int(vq.supplier_id):
        raise ValueError(
            "Nhà cung cấp của PO phải trùng với nhà cung cấp của VQ đã chọn."
        )

    po.po_no = po_no.strip()
    po.supplier_id = int(supplier_id)
    po.status = _to_po_status(status)
    po.order_date = _parse_date(order_date)
    po.expected_date = _parse_date(expected_date)
    po.subtotal = Decimal(str(subtotal or 0))
    po.tax = Decimal(str(tax or 0))
    po.total = Decimal(str(total or 0))
    po.vq_id = int(vq.id)

    _commit()
    return po


def delete_po(po_id: int) -> None:
    po = PurchaseOrder.query.get_or_404(po_id)
    db.session.delete(po)
    _commit()
