# dao/invoice.py
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, exists
from configs import db
from db.models.invoice_payment import VendorInvoice, InvoiceLine, PaymentStatus, Payment
from db.models.purchase import PurchaseOrder

_INV_FORM_TO_ENUM = {
    "draft": PaymentStatus.DRAFT,
    "validated": PaymentStatus.VALIDATED,
    "partially_paid": PaymentStatus.PARTIALLY_PAID,
    "paid": PaymentStatus.PAID,
    "canceled": PaymentStatus.CANCELED,
    "cancelled": PaymentStatus.CANCELED,
}


def _to_inv_status(v: Optional[str]) -> PaymentStatus:
    if not v:
        return PaymentStatus.DRAFT
    return _INV_FORM_TO_ENUM.get(v.strip().lower(), PaymentStatus.DRAFT)


def _to_date(v: Optional[object]) -> Optional[date]:
    if not v:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def _d(x) -> Decimal:
    return Decimal(str(x or 0))


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def list_invoices() -> List[VendorInvoice]:
    return VendorInvoice.query.order_by(
        VendorInvoice.issued_at.desc().nullslast(), VendorInvoice.id.desc()
    ).all()


def get_invoice(invoice_id: int) -> Optional[VendorInvoice]:
    return VendorInvoice.query.get(invoice_id)


def _calc_total(lines: List[Dict]) -> Decimal:
    s = Decimal("0")
    for ln in lines or []:
        s += _d(ln.get("qty")) * _d(ln.get("price"))
    return s


def _has_payment(invoice_id: int) -> bool:
    return db.session.query(exists().where(Payment.invoice_id == invoice_id)).scalar()


def _ensure_editable(inv: VendorInvoice):
    if inv.status in (PaymentStatus.PAID, PaymentStatus.CANCELED):
        raise ValueError("Hóa đơn đã ở trạng thái không cho phép chỉnh sửa.")


def _validate_supplier_matches_po(supplier_id, po_id):
    if not po_id:
        return
    po = PurchaseOrder.query.get(int(po_id))
    if not po:
        raise ValueError("PO không tồn tại.")
    if int(po.supplier_id) != int(supplier_id):
        raise ValueError("Supplier của hóa đơn phải trùng Supplier của PO.")


def _paid_sum(invoice_id: int) -> Decimal:
    s = (
        db.session.query(func.sum(Payment.amount))
        .filter(Payment.invoice_id == invoice_id)
        .scalar()
    )
    return _d(s)


def _update_status_by_payments(inv: VendorInvoice) -> None:
    if inv.status == PaymentStatus.CANCELED:
        return
    paid = _paid_sum(inv.id)
    total = _d(inv.total)
    if total <= 0:
        inv.status = PaymentStatus.PAID
        return
    if paid <= 0:
        if inv.status not in (PaymentStatus.DRAFT, PaymentStatus.VALIDATED):
            inv.status = PaymentStatus.VALIDATED
        return
    inv.status = PaymentStatus.PARTIALLY_PAID if paid < total else PaymentStatus.PAID


def create_invoice(
    supplier_id: int,
    po_id: Optional[int],
    status: str,
    lines: List[Dict],
    issued_at: Optional[object] = None,
) -> VendorInvoice:
    _validate_supplier_matches_po(supplier_id, po_id)
    inv = VendorInvoice(
        supplier_id=int(supplier_id),
        po_id=int(po_id) if po_id else None,
        status=_to_inv_status(status),
        total=Decimal("0"),
        issued_at=_to_date(issued_at),
    )
    db.session.add(inv)
    db.session.flush()

    for ln in lines or []:
        qty = _d(ln.get("qty"))
        price = _d(ln.get("price"))
        db.session.add(
            InvoiceLine(
                invoice_id=inv.id,
                material_id=int(ln["material_id"]),
                qty=qty,
                price=price,
                line_total=qty * price,
            )
        )
    inv.total = _calc_total(lines)

    _commit()
    return inv


def update_invoice(
    invoice_id: int,
    supplier_id: int,
    po_id: Optional[int],
    status: str,
    lines: List[Dict],
    issued_at: Optional[object] = None,
) -> VendorInvoice:
    inv = VendorInvoice.query.get_or_404(invoice_id)
    _ensure_editable(inv)
    _validate_supplier_matches_po(supplier_id, po_id)

    inv.supplier_id = int(supplier_id)
    inv.po_id = int(po_id) if po_id else None
    inv.issued_at = _to_date(issued_at)

    has_pay = _has_payment(inv.id)

    if has_pay:
        # ĐÃ CÓ THANH TOÁN → KHÔNG ĐƯỢC SỬA DÒNG/GIÁ/TỔNG
        # Chỉ cho cập nhật status (DAO sẽ tự điều chỉnh theo số tiền đã thanh toán) và issued_at.
        pass
    else:
        # CHƯA CÓ THANH TOÁN → cho phép sửa lines & total
        InvoiceLine.query.filter_by(invoice_id=inv.id).delete()
        for ln in lines or []:
            qty = _d(ln.get("qty"))
            price = _d(ln.get("price"))
            db.session.add(
                InvoiceLine(
                    invoice_id=inv.id,
                    material_id=int(ln["material_id"]),
                    qty=qty,
                    price=price,
                    line_total=qty * price,
                )
            )
        inv.total = _calc_total(lines)

    # cập nhật trạng thái (ưu tiên theo payments)
    inv.status = _to_inv_status(status)
    _update_status_by_payments(inv)

    _commit()
    return inv


def delete_invoice(invoice_id: int) -> None:
    inv = VendorInvoice.query.get_or_404(invoice_id)

    # Chỉ cho xóa khi DRAFT và chưa có thanh toán
    if inv.status != PaymentStatus.DRAFT:
        raise ValueError("Chỉ có thể xóa hóa đơn ở trạng thái DRAFT.")
    if _has_payment(inv.id):
        raise ValueError("Không thể xóa hóa đơn đã có thanh toán.")

    db.session.delete(inv)
    _commit()
