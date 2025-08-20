from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.supplier import Supplier
from db.models.purchase import PurchaseOrder


def list_suppliers() -> List[Supplier]:
    return Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()


def get_supplier(supplier_id: int) -> Optional[Supplier]:
    return Supplier.query.get(supplier_id)


def create_supplier(
    code: str, name: str, address: str | None, phone: str | None, email: str | None
) -> Supplier:
    s = Supplier(
        code=code.strip(), name=name.strip(), address=address, phone=phone, email=email
    )
    db.session.add(s)
    _commit()
    return s


def update_supplier(supplier_id: int, **fields) -> Supplier:
    s = Supplier.query.get_or_404(supplier_id)
    for k, v in fields.items():
        setattr(s, k, v)
    _commit()
    return s


def delete_supplier(supplier_id: int) -> bool:
    cnt = PurchaseOrder.query.filter_by(supplier_id=supplier_id).count()
    if cnt > 0:
        # tùy bạn: raise AppError hoặc return False để controller flash message
        return False
    sup = Supplier.query.get(supplier_id)
    if not sup:
        return False
    db.session.delete(sup)
    db.session.commit()
    return True


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
