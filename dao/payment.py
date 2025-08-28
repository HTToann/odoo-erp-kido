# dao/payment.py
from typing import Optional
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from configs import db
from db.models.invoice_payment import Payment, VendorInvoice
from dao import invoice as inv_dao


def _d(x):
    return Decimal(str(x or 0))


def _commit():
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        raise


def get_payment(payment_id: int) -> Optional[Payment]:
    return Payment.query.get(payment_id)


def create_payment(invoice_id: int, amount, method: str) -> Payment:
    if Decimal(str(amount or 0)) <= 0:
        raise ValueError("Số tiền thanh toán phải > 0.")
    p = Payment(invoice_id=int(invoice_id), amount=_d(amount), method=method)
    db.session.add(p)
    db.session.flush()
    inv = VendorInvoice.query.get(p.invoice_id)
    inv_dao._update_status_by_payments(inv)
    _commit()
    return p


def update_payment(payment_id: int, invoice_id: int, amount, method: str) -> Payment:
    if Decimal(str(amount or 0)) <= 0:
        raise ValueError("Số tiền thanh toán phải > 0.")
    p = Payment.query.get_or_404(payment_id)
    p.invoice_id = int(invoice_id)
    p.amount = _d(amount)
    p.method = method
    db.session.flush()
    inv = VendorInvoice.query.get(p.invoice_id)
    inv_dao._update_status_by_payments(inv)
    _commit()
    return p


def delete_payment(payment_id: int) -> None:
    p = Payment.query.get_or_404(payment_id)
    inv_id = p.invoice_id
    db.session.delete(p)
    db.session.flush()

    inv = VendorInvoice.query.get(inv_id)
    inv_dao._update_status_by_payments(inv)
    _commit()
