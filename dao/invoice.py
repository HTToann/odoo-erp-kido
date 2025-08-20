from typing import Optional, List, Dict
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.invoice_payment import VendorInvoice, InvoiceLine, PaymentStatus

# ---- map form value (lowercase) -> Enum (UPPERCASE)
_INV_FORM_TO_ENUM = {
    "draft": PaymentStatus.DRAFT,
    "validated": PaymentStatus.VALIDATED,
    "partially_paid": PaymentStatus.PARTIALLY_PAID,
    "paid": PaymentStatus.PAID,
    "canceled": PaymentStatus.CANCELED,
    "cancelled": PaymentStatus.CANCELED,  # chấp nhận cả 2 cách viết
}


def _to_inv_status(value: Optional[str]) -> PaymentStatus:
    if not value:
        return PaymentStatus.DRAFT
    return _INV_FORM_TO_ENUM.get(value.strip().lower(), PaymentStatus.DRAFT)


def list_invoices() -> List[VendorInvoice]:
    return VendorInvoice.query.order_by(VendorInvoice.id.desc()).all()
    # Hoặc: return db.session.execute(db.select(VendorInvoice).order_by(VendorInvoice.id.desc())).scalars().all()


def get_invoice(invoice_id: int) -> Optional[VendorInvoice]:
    return VendorInvoice.query.get(invoice_id)
    # Hoặc: return db.session.get(VendorInvoice, invoice_id)


def _calc_total(lines: List[Dict]) -> Decimal:
    s = Decimal("0")
    for ln in lines or []:
        s += Decimal(str(ln.get("qty", 0))) * Decimal(str(ln.get("price", 0)))
    return s


def create_invoice(
    supplier_id: int, po_id: int | None, status: str, lines: List[Dict]
) -> VendorInvoice:
    inv = VendorInvoice(
        supplier_id=int(supplier_id),
        po_id=int(po_id) if po_id else None,
        status=_to_inv_status(status),  # <-- QUAN TRỌNG
        total=Decimal("0"),
    )
    db.session.add(inv)
    db.session.flush()
    for ln in lines or []:
        db.session.add(
            InvoiceLine(
                invoice_id=inv.id,
                material_id=int(ln["material_id"]),
                qty=Decimal(str(ln.get("qty", 0))),
                price=Decimal(str(ln.get("price", 0))),
                line_total=Decimal(str(ln.get("qty", 0)))
                * Decimal(str(ln.get("price", 0))),
            )
        )
    inv.total = _calc_total(lines)
    _commit()
    return inv


def update_invoice(
    invoice_id: int, supplier_id: int, po_id: int | None, status: str, lines: List[Dict]
) -> VendorInvoice:
    inv = VendorInvoice.query.get_or_404(invoice_id)
    inv.supplier_id = int(supplier_id)
    inv.po_id = int(po_id) if po_id else None
    inv.status = _to_inv_status(status)  # <-- QUAN TRỌNG

    InvoiceLine.query.filter_by(invoice_id=inv.id).delete()
    for ln in lines or []:
        db.session.add(
            InvoiceLine(
                invoice_id=inv.id,
                material_id=int(ln["material_id"]),
                qty=Decimal(str(ln.get("qty", 0))),
                price=Decimal(str(ln.get("price", 0))),
                line_total=Decimal(str(ln.get("qty", 0)))
                * Decimal(str(ln.get("price", 0))),
            )
        )
    inv.total = _calc_total(lines)
    _commit()
    return inv


def delete_invoice(invoice_id: int) -> None:
    inv = VendorInvoice.query.get_or_404(invoice_id)
    db.session.delete(inv)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
