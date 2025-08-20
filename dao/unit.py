from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.unit import Unit
from db.models.material import Material
from decimal import Decimal


class UnitInUseError(Exception):
    pass


def _is_unit_in_use(unit_id: int) -> bool:
    # Chỉ cần biết có 1 record dùng là đủ; limit(1) cho nhanh
    return (
        db.session.query(Material.id).filter_by(unit_id=unit_id).limit(1).first()
        is not None
    )


def list_units() -> List[Unit]:
    return Unit.query.order_by(Unit.code.asc()).all()


def get_unit(unit_id: int) -> Optional[Unit]:
    return Unit.query.get(unit_id)


def create_unit(code: str, name: str, base_factor) -> Unit:
    bf = Decimal(str(base_factor or 1))
    u = Unit(code=code.strip(), name=name.strip(), base_factor=bf)
    db.session.add(u)
    _commit()
    return u


def update_unit(unit_id: int, **fields) -> Unit:
    u = Unit.query.get_or_404(unit_id)

    # Nếu unit đang được dùng => không cho chỉnh sửa
    if _is_unit_in_use(unit_id):
        raise UnitInUseError("Đơn vị đang được sử dụng, không thể chỉnh sửa.")

    # Convert base_factor về Decimal nếu được truyền
    if "base_factor" in fields and fields["base_factor"] is not None:
        from decimal import Decimal

        fields["base_factor"] = Decimal(str(fields["base_factor"]))

    for k, v in fields.items():
        setattr(u, k, v)

    _commit()
    return u


def delete_unit(unit_id: int) -> None:
    # Không cho xoá nếu đang được dùng
    if _is_unit_in_use(unit_id):
        raise UnitInUseError("Đơn vị đang được sử dụng, không thể xoá.")

    u = Unit.query.get_or_404(unit_id)
    db.session.delete(u)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
