from typing import List, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.vendor_quotation import (
    VendorQuotation,
    VendorQuotationLine,
    VendorQuotationStatus,
)
from db.models.purchase import PurchaseOrder, POStatus, PurchaseOrderItem
from dao import rfq as rfq_dao
from sqlalchemy import exists

# map string từ form -> Enum (nhận cả lowercase)
_VQ_FORM_TO_ENUM = {
    "received": VendorQuotationStatus.RECEIVED,
    "selected": VendorQuotationStatus.SELECTED,
    "rejected": VendorQuotationStatus.REJECTED,
}


def build_lines_from_rfq(rfq_id: int) -> List[Dict]:
    """Chuẩn bị lines cho VQ: giữ nguyên material/qty, price = 0."""
    base = rfq_dao.get_rfq_lines_as_dicts(rfq_id)
    return [
        {"material_id": x["material_id"], "qty": x["qty"], "price": 0.0} for x in base
    ]


def create_vq_from_rfq(
    rfq_id: int, supplier_id: int, status: str = "received"
) -> VendorQuotation:
    lines = build_lines_from_rfq(rfq_id)
    return create_vq(rfq_id=rfq_id, supplier_id=supplier_id, status=status, lines=lines)


def _to_vq_status(value: Optional[str]) -> VendorQuotationStatus:
    if not value:
        return VendorQuotationStatus.RECEIVED
    return _VQ_FORM_TO_ENUM.get(value.strip().lower(), VendorQuotationStatus.RECEIVED)


# ======== Queries ========
def list_vqs() -> List[VendorQuotation]:
    return VendorQuotation.query.order_by(VendorQuotation.id.desc()).all()


def get_vq(vq_id: int) -> Optional[VendorQuotation]:
    return VendorQuotation.query.get(vq_id)


# ======== Mutations ========
def create_vq(
    rfq_id: Optional[int], supplier_id: Optional[int], status: str, lines: list[dict]
) -> VendorQuotation:
    if not rfq_id:
        raise ValueError("Vui lòng chọn RFQ trước khi tạo VQ.")

    rfq = rfq_dao.get_rfq(int(rfq_id))
    if not rfq:
        raise ValueError("RFQ không tồn tại.")
    if rfq.status != rfq_dao._to_rfq_status("APPROVED"):
        raise ValueError("Chỉ có thể tạo VQ từ RFQ đã được APPROVED.")

    norm_lines = _normalize_vq_lines(lines)

    vq = VendorQuotation(
        rfq_id=rfq.id,
        supplier_id=int(supplier_id) if supplier_id else None,
        status=_to_vq_status(status),
    )
    db.session.add(vq)
    db.session.flush()

    for ln in norm_lines:
        db.session.add(
            VendorQuotationLine(
                vq=vq,
                material_id=ln["material_id"],
                qty=ln["qty"],
                price=ln["price"],
            )
        )

    _commit()
    return vq


def update_vq(
    vq_id: int,
    rfq_id: Optional[int],
    supplier_id: Optional[int],
    status: str,
    lines: List[Dict],
) -> Optional[VendorQuotation]:
    vq = get_vq(vq_id)
    if not vq:
        return None

    # Cấm sửa nếu VQ đã được dùng để tạo PO
    _ensure_vq_not_used_by_po(vq.id)

    # Nếu đổi RFQ -> RFQ phải tồn tại & APPROVED
    if rfq_id is not None:
        rfq = rfq_dao.get_rfq(int(rfq_id))
        if not rfq:
            raise ValueError("RFQ không tồn tại.")
        if rfq.status != rfq_dao._to_rfq_status("APPROVED"):
            raise ValueError("Chỉ có thể gán VQ tới RFQ đã APPROVED.")
        vq.rfq_id = rfq.id

    vq.supplier_id = int(supplier_id) if supplier_id else None
    new_status = _to_vq_status(status)

    # Nếu set SELECTED -> đảm bảo không có VQ SELECTED khác thuộc cùng RFQ
    if new_status == VendorQuotationStatus.SELECTED:
        if not vq.rfq_id:
            raise ValueError("VQ phải gắn với RFQ trước khi SELECTED.")
        _ensure_no_other_selected_for_rfq(vq.rfq_id, exclude_vq_id=vq.id)
    vq.status = new_status

    # thay toàn bộ lines (đã validate)
    vq.lines.clear()
    db.session.flush()
    norm_lines = _normalize_vq_lines(lines)
    for ln in norm_lines:
        db.session.add(
            VendorQuotationLine(
                vq=vq,
                material_id=ln["material_id"],
                qty=ln["qty"],
                price=ln["price"],
            )
        )

    _commit()
    return vq


def delete_vq(vq_id: int) -> bool:
    vq = get_vq(vq_id)
    if not vq:
        return False
    db.session.delete(vq)
    _commit()
    return True


def _dec(x) -> Decimal:
    return Decimal(str(x or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(d):
    if isinstance(d, datetime) or d is None:
        return d
    d = str(d).strip()
    if not d:
        return None
    return datetime.strptime(d, "%Y-%m-%d")


def create_po_from_vq(
    vq_id: int,
    po_no: str,
    *,
    status: str = "DRAFT",
    order_date: Optional[str | datetime] = None,
    expected_date: Optional[str | datetime] = None,
    tax_rate: Optional[float] = None,
    tax_amount: Optional[float] = None,
) -> PurchaseOrder:
    vq: VendorQuotation | None = VendorQuotation.query.get(vq_id)
    if not vq:
        raise ValueError(f"VendorQuotation #{vq_id} không tồn tại")

    if vq.status != VendorQuotationStatus.SELECTED:
        raise ValueError("Chỉ có thể tạo PO từ VQ ở trạng thái SELECTED.")

    # 1 VQ chỉ được tạo đúng 1 PO
    if db.session.query(exists().where(PurchaseOrder.vq_id == vq.id)).scalar():
        raise ValueError("VQ này đã được dùng để tạo PO khác.")

    if not vq.lines:
        raise ValueError("VQ không có dòng báo giá, không thể tạo PO")

    # Tính tiền từ dòng báo giá (và qty/price phải hợp lệ)
    subtotal = Decimal("0.00")
    for idx, ln in enumerate(vq.lines, 1):
        qty = _dec(ln.qty)
        price = _dec(ln.price)
        if qty <= 0:
            raise ValueError(f"Dòng VQ #{idx}: qty phải > 0.")
        if price < 0:
            raise ValueError(f"Dòng VQ #{idx}: price không được âm.")
        subtotal += qty * price

    if tax_amount is not None:
        tax = _dec(tax_amount)
    elif tax_rate is not None:
        tax = (subtotal * _dec(tax_rate)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        tax = Decimal("0.00")

    total = (subtotal + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    st = str(status or "DRAFT").strip().upper()
    try:
        po_status = POStatus[st]
    except KeyError:
        po_status = POStatus.DRAFT

    po = PurchaseOrder(
        po_no=po_no.strip(),
        supplier_id=vq.supplier_id,
        status=po_status,
        order_date=_parse_date(order_date),
        expected_date=_parse_date(expected_date),
        subtotal=subtotal,
        tax=tax,
        total=total,
        vq_id=vq.id,
    )
    db.session.add(po)
    db.session.flush()

    for ln in vq.lines:
        db.session.add(
            PurchaseOrderItem(
                po_id=po.id,
                material_id=ln.material_id,
                qty=_dec(ln.qty),
                price=_dec(ln.price),
                line_total=(_dec(ln.qty) * _dec(ln.price)).quantize(Decimal("0.01")),
            )
        )

    _commit()
    return po


def _normalize_vq_lines(lines: list[dict]) -> list[dict]:
    if not lines:
        raise ValueError("Vui lòng nhập ít nhất 1 dòng báo giá.")
    out = []
    for idx, ln in enumerate(lines, 1):
        try:
            material_id = int(ln["material_id"])
        except Exception:
            raise ValueError(f"Dòng {idx}: thiếu hoặc sai material_id.")
        try:
            qty = float(ln.get("qty", 0) or 0)
        except Exception:
            raise ValueError(f"Dòng {idx}: qty không hợp lệ.")
        try:
            price = float(ln.get("price", 0) or 0)
        except Exception:
            raise ValueError(f"Dòng {idx}: price không hợp lệ.")
        if qty <= 0:
            raise ValueError(f"Dòng {idx}: qty phải > 0.")
        if price < 0:
            raise ValueError(f"Dòng {idx}: price không được âm.")
        out.append({"material_id": material_id, "qty": qty, "price": price})
    return out


def _ensure_no_other_selected_for_rfq(rfq_id: int, exclude_vq_id: int | None = None):
    q = VendorQuotation.query.filter(
        VendorQuotation.rfq_id == int(rfq_id),
        VendorQuotation.status == VendorQuotationStatus.SELECTED,
    )
    if exclude_vq_id:
        q = q.filter(VendorQuotation.id != int(exclude_vq_id))
    if db.session.query(q.exists()).scalar():
        raise ValueError("Đã có VQ khác của RFQ này ở trạng thái SELECTED.")


def _ensure_vq_not_used_by_po(vq_id: int):
    used = db.session.query(exists().where(PurchaseOrder.vq_id == int(vq_id))).scalar()
    if used:
        raise ValueError("VQ đã được dùng để tạo PO, không thể chỉnh sửa.")


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
