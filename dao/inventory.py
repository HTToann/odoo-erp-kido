# dao/inventory.py
from decimal import Decimal
from typing import Optional
from configs import db
from db.models.inventory import StockItem, StockMovement
from sqlalchemy import func
from typing import Iterable


def _dec(x) -> Decimal:
    return Decimal(str(x or 0))


def sync_stock_items(material_ids: Iterable[int]) -> None:
    """Cập nhật qty_on_hand cho danh sách material_ids theo tổng StockMovement."""
    material_ids = list(set(int(x) for x in material_ids if x is not None))
    if not material_ids:
        return

    # Lấy tổng movement theo vật tư
    totals = {
        mid: float(total or 0)
        for (mid, total) in db.session.query(
            StockMovement.material_id, func.sum(StockMovement.qty_change)
        )
        .filter(StockMovement.material_id.in_(material_ids))
        .group_by(StockMovement.material_id)
        .all()
    }

    # Upsert vào StockItem
    for mid in material_ids:
        total = totals.get(mid, 0.0)
        si = StockItem.query.filter_by(material_id=mid).one_or_none()
        if si:
            si.qty_on_hand = total
        else:
            db.session.add(StockItem(material_id=mid, qty_on_hand=total))


def ensure_stock_item(material_id: int) -> StockItem:
    si = StockItem.query.filter_by(material_id=material_id).first()
    if not si:
        si = StockItem(material_id=material_id, qty_on_hand=_dec(0))
        db.session.add(si)
        db.session.flush()
    return si


def bump_stock(material_id: int, delta) -> None:
    """Cộng/trừ tồn ngay theo delta."""
    si = ensure_stock_item(material_id)
    si.qty_on_hand = _dec(si.qty_on_hand) + _dec(delta)


def remove_movements(ref_type: str, ref_id: int) -> None:
    """
    Xóa các movement theo ref_type/ref_id và TRỪ tồn kho tương ứng (rollback).
    Dùng khi re-post hoặc xóa chứng từ.
    """
    mvs = StockMovement.query.filter_by(ref_type=ref_type, ref_id=ref_id).all()
    for mv in mvs:
        bump_stock(mv.material_id, -_dec(mv.qty_change))
        db.session.delete(mv)


def add_movement(
    material_id: int, ref_type: str, ref_id: int, qty_change
) -> StockMovement:
    """
    Ghi 1 movement và CỘNG tồn kho tương ứng.
    """
    mv = StockMovement(
        material_id=material_id,
        ref_type=ref_type,
        ref_id=ref_id,
        qty_change=_dec(qty_change),
    )
    db.session.add(mv)
    bump_stock(material_id, qty_change)
    return mv
