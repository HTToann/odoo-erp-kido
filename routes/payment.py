from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import payment as pay_dao, invoice as inv_dao

payment_bp = Blueprint("payment_web", __name__)


@payment_bp.route("/payments/add/<int:invoice_id>", methods=["GET", "POST"])
@login_required
def payment_add(invoice_id: int):
    if request.method == "POST":
        amount = request.form.get("amount")
        method = request.form.get("method", "bank")
        pay_dao.create_payment(invoice_id, amount, method)
        flash("Thanh toán thành công", "success")
        return redirect(url_for("invoice_web.invoice_list"))
    invoices = inv_dao.list_invoices()
    payment = None
    return render_template(
        "payment_form.html", action="add", payment=payment, invoices=invoices
    )


@payment_bp.route("/payments/edit/<int:payment_id>", methods=["GET", "POST"])
@login_required
def payment_edit(payment_id: int):
    p = pay_dao.get_payment(payment_id)
    if not p:
        flash("Không tìm thấy chứng từ thanh toán", "warning")
        return redirect(url_for("invoice_web.invoice_list"))
    if request.method == "POST":
        amount = request.form.get("amount")
        method = request.form.get("method", "bank")
        invoice_id = request.form.get("invoice_id")
        pay_dao.update_payment(payment_id, invoice_id, amount, method)
        flash("Cập nhật thanh toán thành công", "success")
        return redirect(url_for("invoice_web.invoice_list"))
    invoices = inv_dao.list_invoices()
    return render_template(
        "payment_form.html", action="edit", payment=p, invoices=invoices
    )


@payment_bp.route("/payments/delete/<int:payment_id>", methods=["POST"])
@login_required
def payment_delete(payment_id: int):
    pay_dao.delete_payment(payment_id)
    flash("Xóa chứng từ thanh toán thành công", "success")
    return redirect(url_for("invoice_web.invoice_list"))
