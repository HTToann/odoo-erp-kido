from typing import Optional
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.invoice_payment import Payment


def get_payment(payment_id: int) -> Optional[Payment]:
    return Payment.query.get(payment_id)


def create_payment(invoice_id: int, amount, method: str) -> Payment:
    p = Payment(
        invoice_id=int(invoice_id), amount=Decimal(str(amount or 0)), method=method
    )
    db.session.add(p)
    _commit()
    return p


def update_payment(payment_id: int, invoice_id: int, amount, method: str) -> Payment:
    p = Payment.query.get_or_404(payment_id)
    p.invoice_id = int(invoice_id)
    p.amount = Decimal(str(amount or 0))
    p.method = method
    _commit()
    return p


def delete_payment(payment_id: int) -> None:
    p = Payment.query.get_or_404(payment_id)
    db.session.delete(p)
    _commit()


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise
