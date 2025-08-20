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
    rfq_id: Optional[int], supplier_id: Optional[int], status: str, lines: List[Dict]
) -> VendorQuotation:
    vq = VendorQuotation(
        rfq_id=int(rfq_id) if rfq_id else None,
        supplier_id=int(supplier_id) if supplier_id else None,
        status=_to_vq_status(status),
    )
    db.session.add(vq)
    db.session.flush()  # cần vq.id

    for ln in lines or []:
        material_id = ln.get("material_id")
        if not material_id:  # bỏ qua dòng thiếu vật tư
            continue
        db.session.add(
            VendorQuotationLine(
                vq=vq,
                material_id=int(material_id),
                qty=float(ln.get("qty", 0) or 0),
                price=float(ln.get("price", 0) or 0),
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

    vq.rfq_id = int(rfq_id) if rfq_id else None
    vq.supplier_id = int(supplier_id) if supplier_id else None
    vq.status = _to_vq_status(status)

    # thay toàn bộ lines
    vq.lines.clear()
    db.session.flush()
    for ln in lines or []:
        material_id = ln.get("material_id")
        if not material_id:
            continue
        db.session.add(
            VendorQuotationLine(
                vq=vq,
                material_id=int(material_id),
                qty=float(ln.get("qty", 0) or 0),
                price=float(ln.get("price", 0) or 0),
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
    tax_rate: Optional[float] = None,  # vd: 0.08 cho 8%
    tax_amount: Optional[float] = None,  # nếu muốn chỉ định thẳng
) -> PurchaseOrder:
    """
    Tạo PO từ VQ: copy supplier + lines, tính subtotal/tax/total, sinh PurchaseOrderItem.
    - Một trong tax_rate hoặc tax_amount có thể dùng (ưu tiên tax_amount nếu có).
    """
    vq: VendorQuotation | None = VendorQuotation.query.get(vq_id)
    if not vq:
        raise ValueError(f"VendorQuotation #{vq_id} không tồn tại")

    if not vq.lines:
        raise ValueError("VQ không có dòng báo giá, không thể tạo PO")

    # Tính tiền từ dòng báo giá
    subtotal = Decimal("0.00")
    for ln in vq.lines:
        subtotal += _dec(ln.qty) * _dec(ln.price)

    if tax_amount is not None:
        tax = _dec(tax_amount)
    elif tax_rate is not None:
        tax = (subtotal * _dec(tax_rate)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    else:
        tax = Decimal("0.00")

    total = (subtotal + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Chuẩn hóa status enum
    st = str(status or "DRAFT").strip().upper()
    try:
        po_status = POStatus[st]
    except KeyError:
        po_status = POStatus.DRAFT

    # Parse date từ string 'YYYY-MM-DD' nếu cần

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
    db.session.flush()  # có po.id

    # Sinh các items từ VendorQuotationLine
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


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
