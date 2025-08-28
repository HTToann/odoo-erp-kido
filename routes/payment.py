# routes/payments.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import payment as pay_dao, invoice as inv_dao

payment_bp = Blueprint("payment_web", __name__)


@payment_bp.route("/payments/add", methods=["GET", "POST"])
@login_required
def payment_add():
    invoice_id = request.args.get("invoice_id")
    if request.method == "POST":
        invoice_id = request.form.get("invoice_id")
        amount = request.form.get("amount")
        method = request.form.get("method", "bank")
        try:
            pay_dao.create_payment(invoice_id, amount, method)
            flash("Đã ghi thanh toán.", "success")
        except Exception as ex:
            flash(str(ex), "danger")
        return redirect(url_for("invoice_web.invoice_list"))
    invoices = inv_dao.list_invoices()
    return render_template(
        "invoice/payment_form.html", action="add", payment=None, invoices=invoices
    )


@payment_bp.route("/payments/edit/<int:payment_id>", methods=["GET", "POST"])
@login_required
def payment_edit(payment_id: int):
    payment = pay_dao.get_payment(payment_id)
    if not payment:
        flash("Không tìm thấy payment", "warning")
        return redirect(url_for("invoice_web.invoice_list"))
    if request.method == "POST":
        invoice_id = request.form.get("invoice_id")
        amount = request.form.get("amount")
        method = request.form.get("method", "bank")
        try:
            pay_dao.update_payment(payment_id, invoice_id, amount, method)
            flash("Đã cập nhật thanh toán.", "success")
        except Exception as ex:
            flash(str(ex), "danger")
        return redirect(url_for("invoice_web.invoice_list"))
    invoices = inv_dao.list_invoices()
    return render_template(
        "invoice/payment_form.html", action="edit", payment=payment, invoices=invoices
    )


@payment_bp.route("/payments/delete/<int:payment_id>", methods=["POST"])
@login_required
def payment_delete(payment_id: int):
    try:
        pay_dao.delete_payment(payment_id)
        flash("Đã xóa thanh toán.", "success")
    except Exception as ex:
        flash(str(ex), "danger")
    return redirect(url_for("invoice_web.invoice_list"))
