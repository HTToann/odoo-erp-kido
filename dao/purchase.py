# dao/purchase.py
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, case
from configs import db
from db.models.purchase import PurchaseOrder, PurchaseOrderItem, POStatus
from db.models.goods_receipt import GoodsReceipt, GRLine, GRStatus


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


def list_purchases_confirmed():
    return (
        PurchaseOrder.query.filter(PurchaseOrder.status == POStatus.CONFIRMED)
        .order_by(PurchaseOrder.id.desc())
        .all()
    )


def po_lines_with_remaining(po_id: int):
    """
    Trả về list dict: {po_line_id, material_id, material, ordered, received, remaining}
    """
    # ordered
    q = (
        db.session.query(
            PurchaseOrderItem.id.label("po_line_id"),
            PurchaseOrderItem.material_id,
            PurchaseOrderItem.qty.label("ordered"),
            func.coalesce(
                func.sum(
                    db.case(
                        (
                            GoodsReceipt.status.in_(
                                [GRStatus.CHECKED, GRStatus.POSTED]
                            ),
                            GRLine.qty,
                        ),
                        else_=0,
                    )
                ),
                0,
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
                "material_id": r.material_id,
                "ordered": float(r.ordered or 0),
                "received": float(r.received or 0),
                "remaining": max(0.0, remaining),
            }
        )
    return rows


def get_po(po_id: int) -> Optional[PurchaseOrder]:
    return PurchaseOrder.query.get(po_id)


def create_po(
    po_no: str,
    supplier_id: int,
    status: str,
    order_date,
    expected_date,
    subtotal,
    tax,
    total,
    vq_id: int | None = None,  # 👈 thêm vq_id
) -> PurchaseOrder:
    po = PurchaseOrder(
        po_no=po_no.strip(),
        supplier_id=int(supplier_id),
        status=_to_po_status(status),
        order_date=_parse_date(order_date),
        expected_date=_parse_date(expected_date),
        subtotal=Decimal(str(subtotal or 0)),
        tax=Decimal(str(tax or 0)),
        total=Decimal(str(total or 0)),
        vq_id=int(vq_id) if vq_id else None,  # 👈 map sang model
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
    vq_id: int | None = None,  # 👈 cho phép cập nhật vq_id
) -> PurchaseOrder:
    po = PurchaseOrder.query.get_or_404(po_id)
    po.po_no = po_no.strip()
    po.supplier_id = int(supplier_id)
    po.status = _to_po_status(status)
    po.order_date = _parse_date(order_date)
    po.expected_date = _parse_date(expected_date)
    po.subtotal = Decimal(str(subtotal or 0))
    po.tax = Decimal(str(tax or 0))
    po.total = Decimal(str(total or 0))
    po.vq_id = int(vq_id) if vq_id else None
    _commit()
    return po


def delete_po(po_id: int) -> None:
    po = PurchaseOrder.query.get_or_404(po_id)
    db.session.delete(po)
    _commit()


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
