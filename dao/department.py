from typing import Optional, List
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.department import Department


def list_departments() -> List[Department]:
    return Department.query.order_by(Department.code.asc()).all()


def get_department(dept_id: int) -> Optional[Department]:
    return Department.query.get(dept_id)


def create_department(code: str, name: str) -> Department:
    d = Department(code=code.strip(), name=name.strip())
    db.session.add(d)
    _commit()
    return d


def update_department(dept_id: int, **fields) -> Department:
    d = Department.query.get_or_404(dept_id)
    for k, v in fields.items():
        setattr(d, k, v)
    _commit()
    return d


def delete_department(dept_id: int) -> None:
    d = Department.query.get_or_404(dept_id)
    db.session.delete(d)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
