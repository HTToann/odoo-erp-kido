from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import supplier as supplier_dao

supplier_bp = Blueprint("supplier_web", __name__)


@supplier_bp.route("/suppliers")
@login_required
def suppliers_list():
    suppliers = supplier_dao.list_suppliers()
    return render_template("supplier/suppliers.html", suppliers=suppliers)


@supplier_bp.route("/suppliers/add", methods=["GET", "POST"])
@login_required
def suppliers_add():
    if request.method == "POST":
        supplier_dao.create_supplier(
            code=request.form.get("code", ""),
            name=request.form.get("name", ""),
            address=request.form.get("address"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
        )
        flash("Thêm nhà cung cấp thành công", "success")
        return redirect(url_for("supplier_web.suppliers_list"))
    return render_template("supplier/supplier_form.html", action="add")


@supplier_bp.route("/suppliers/edit/<int:supplier_id>", methods=["GET", "POST"])
@login_required
def suppliers_edit(supplier_id: int):
    s = supplier_dao.get_supplier(supplier_id)
    if not s:
        flash("Không tìm thấy nhà cung cấp", "warning")
        return redirect(url_for("supplier_web.suppliers_list"))
    if request.method == "POST":
        supplier_dao.update_supplier(
            supplier_id,
            code=request.form.get("code", ""),
            name=request.form.get("name", ""),
            address=request.form.get("address"),
            phone=request.form.get("phone"),
            email=request.form.get("email"),
        )
        flash("Cập nhật nhà cung cấp thành công", "success")
        return redirect(url_for("supplier_web.suppliers_list"))
    return render_template("supplier/supplier_form.html", action="edit", supplier=s)


@supplier_bp.route("/suppliers/delete/<int:supplier_id>", methods=["POST"])
@login_required
def suppliers_delete(supplier_id: int):
    ok = supplier_dao.delete_supplier(supplier_id)
    if not ok:
        flash(
            "Không thể xóa: Nhà cung cấp đang được dùng trong đơn mua hàng.", "warning"
        )
    else:
        flash("Xóa nhà cung cấp thành công", "success")
    return redirect(url_for("supplier_web.suppliers_list"))
