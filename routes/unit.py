from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import unit as unit_dao
from dao.unit import UnitInUseError

unit_bp = Blueprint("unit_web", __name__)


@unit_bp.route("/units")
@login_required
def units_list():
    units = unit_dao.list_units()
    return render_template("unit/units.html", units=units)


@unit_bp.route("/units/add", methods=["GET", "POST"])
@login_required
def units_add():
    if request.method == "POST":
        unit_dao.create_unit(
            code=request.form.get("code", ""),
            name=request.form.get("name", ""),
            base_factor=request.form.get("base_factor", 1),
        )
        flash("Thêm đơn vị thành công", "success")
        return redirect(url_for("unit_web.units_list"))
    return render_template("unit/unit_form.html", action="add")


@unit_bp.route("/units/edit/<int:unit_id>", methods=["GET", "POST"])
@login_required
def units_edit(unit_id: int):
    u = unit_dao.get_unit(unit_id)  # hoặc Unit.query.get_or_404(...)
    if not u:
        flash("Không tìm thấy đơn vị", "warning")
        return redirect(url_for("unit_web.units_list"))

    if request.method == "POST":
        try:
            unit_dao.update_unit(
                unit_id,
                code=request.form.get("code", ""),
                name=request.form.get("name", ""),
                base_factor=request.form.get("base_factor", 1),
                is_active=1 if request.form.get("is_active") else 0,
            )
            flash("Cập nhật đơn vị thành công", "success")
        except UnitInUseError as e:
            flash(str(e), "warning")
        return redirect(url_for("unit_web.units_list"))

    return render_template("unit/unit_form.html", action="edit", unit=u)


@unit_bp.route("/units/delete/<int:unit_id>", methods=["POST"])
@login_required
def units_delete(unit_id: int):
    try:
        unit_dao.delete_unit(unit_id)
        flash("Xóa đơn vị thành công", "success")
    except UnitInUseError as e:
        flash(str(e), "warning")
    return redirect(url_for("unit_web.units_list"))
