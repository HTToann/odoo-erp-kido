from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.material import Material


def list_materials() -> List[Material]:
    return Material.query.order_by(Material.sku.asc()).all()


def get_material(material_id: int) -> Optional[Material]:
    return Material.query.get(material_id)


def create_material(
    sku: str, name: str, category: str | None, unit_id: int
) -> Material:
    m = Material(
        sku=sku.strip(), name=name.strip(), category=category, unit_id=int(unit_id)
    )
    db.session.add(m)
    _commit()
    return m


def update_material(material_id: int, **fields) -> Material:
    m = Material.query.get_or_404(material_id)
    for k, v in fields.items():
        if k == "unit_id" and v is not None:
            v = int(v)
        setattr(m, k, v)
    _commit()
    return m


def delete_material(material_id: int) -> None:
    m = Material.query.get_or_404(material_id)
    db.session.delete(m)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
