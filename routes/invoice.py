from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import (
    invoice as inv_dao,
    supplier as supplier_dao,
    purchase as po_dao,
    material as material_dao,
)

invoice_bp = Blueprint("invoice_web", __name__)


@invoice_bp.route("/invoices")
@login_required
def invoice_list():
    invoices = inv_dao.list_invoices()
    return render_template("invoice/invoice_payment.html", invoices=invoices)


@invoice_bp.route("/invoices/add", methods=["GET", "POST"])
@login_required
def invoice_add():
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id")
        po_id = request.form.get("po_id")
        status = request.form.get("status", "draft")
        lines = _extract_lines(request)  # material_id, qty, price
        inv_dao.create_invoice(supplier_id, po_id, status, lines)
        flash("Tạo hóa đơn thành công", "success")
        return redirect(url_for("invoice_web.invoice_list"))
    suppliers = supplier_dao.list_suppliers()
    purchases = po_dao.list_purchases()
    materials = material_dao.list_materials()
    return render_template(
        "invoice/invoice_form.html",
        action="add",
        inv=None,
        suppliers=suppliers,
        purchases=purchases,
        materials=materials,
    )


@invoice_bp.route("/invoices/edit/<int:invoice_id>", methods=["GET", "POST"])
@login_required
def invoice_edit(invoice_id: int):
    inv = inv_dao.get_invoice(invoice_id)
    if not inv:
        flash("Không tìm thấy hóa đơn", "warning")
        return redirect(url_for("invoice_web.invoice_list"))
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id")
        po_id = request.form.get("po_id")
        status = request.form.get("status", "draft")
        lines = _extract_lines(request)
        inv_dao.update_invoice(invoice_id, supplier_id, po_id, status, lines)
        flash("Cập nhật hóa đơn thành công", "success")
        return redirect(url_for("invoice_web.invoice_list"))
    suppliers = supplier_dao.list_suppliers()
    purchases = po_dao.list_purchases()
    materials = material_dao.list_materials()
    return render_template(
        "invoice/invoice_form.html",
        action="edit",
        inv=inv,
        suppliers=suppliers,
        purchases=purchases,
        materials=materials,
    )


@invoice_bp.route("/invoices/delete/<int:invoice_id>", methods=["POST"])
@login_required
def invoice_delete(invoice_id: int):
    inv_dao.delete_invoice(invoice_id)
    flash("Xóa hóa đơn thành công", "success")
    return redirect(url_for("invoice_web.invoice_list"))


def _extract_lines(req):
    lines = []
    for key in req.form:
        if key.startswith("lines[") and key.endswith("][material_id]"):
            idx = key.split("[")[1].split("]")[0]
            material_id = req.form.get(f"lines[{idx}][material_id]")
            qty = req.form.get(f"lines[{idx}][qty]")
            price = req.form.get(f"lines[{idx}][price]")
            if material_id and qty is not None and price is not None:
                lines.append(
                    {
                        "material_id": int(material_id),
                        "qty": float(qty or 0),
                        "price": float(price or 0),
                    }
                )
    return lines
