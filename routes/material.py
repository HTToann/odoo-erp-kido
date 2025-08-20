from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import material as material_dao, unit as unit_dao

material_bp = Blueprint("material_web", __name__)


@material_bp.route("/materials")
@login_required
def materials_list():
    materials = material_dao.list_materials()
    return render_template("material/materials.html", materials=materials)


@material_bp.route("/materials/add", methods=["GET", "POST"])
@login_required
def materials_add():
    if request.method == "POST":
        material_dao.create_material(
            sku=request.form.get("sku", ""),
            name=request.form.get("name", ""),
            category=request.form.get("category"),
            unit_id=request.form.get("unit_id"),
        )
        flash("Thêm nguyên liệu thành công", "success")
        return redirect(url_for("material_web.materials_list"))
    units = unit_dao.list_units()
    return render_template(
        "material/material_form.html", action="add", material=None, units=units
    )


@material_bp.route("/materials/edit/<int:material_id>", methods=["GET", "POST"])
@login_required
def materials_edit(material_id: int):
    m = material_dao.get_material(material_id)
    if not m:
        flash("Không tìm thấy nguyên liệu", "warning")
        return redirect(url_for("material_web.materials_list"))
    if request.method == "POST":
        material_dao.update_material(
            material_id,
            sku=request.form.get("sku", ""),
            name=request.form.get("name", ""),
            category=request.form.get("category"),
            unit_id=request.form.get("unit_id"),
        )
        flash("Cập nhật nguyên liệu thành công", "success")
        return redirect(url_for("material_web.materials_list"))
    units = unit_dao.list_units()
    return render_template(
        "material/material_form.html", action="edit", material=m, units=units
    )


@material_bp.route("/materials/delete/<int:material_id>", methods=["POST"])
@login_required
def materials_delete(material_id: int):
    material_dao.delete_material(material_id)
    flash("Xóa nguyên liệu thành công", "success")
    return redirect(url_for("material_web.materials_list"))
