from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import department as department_dao

department_bp = Blueprint("department_web", __name__)


@department_bp.route("/departments")
@login_required
def departments_list():
    deps = department_dao.list_departments()
    return render_template("department/departments.html", departments=deps)


@department_bp.route("/departments/add", methods=["GET", "POST"])
@login_required
def departments_add():
    if request.method == "POST":
        department_dao.create_department(
            code=request.form.get("code", ""),
            name=request.form.get("name", ""),
        )
        flash("Thêm phòng ban thành công", "success")
        return redirect(url_for("department_web.departments_list"))
    return render_template(
        "department/department_form.html", action="add", department=None
    )


@department_bp.route("/departments/edit/<int:dept_id>", methods=["GET", "POST"])
@login_required
def departments_edit(dept_id: int):
    d = department_dao.get_department(dept_id)
    if not d:
        flash("Không tìm thấy phòng ban", "warning")
        return redirect(url_for("department_web.departments_list"))
    if request.method == "POST":
        department_dao.update_department(
            dept_id,
            code=request.form.get("code", ""),
            name=request.form.get("name", ""),
        )
        flash("Cập nhật phòng ban thành công", "success")
        return redirect(url_for("department_web.departments_list"))
    return render_template(
        "department/department_form.html", action="edit", department=d
    )


@department_bp.route("/departments/delete/<int:dept_id>", methods=["POST"])
@login_required
def departments_delete(dept_id: int):
    department_dao.delete_department(dept_id)
    flash("Xóa phòng ban thành công", "success")
    return redirect(url_for("department_web.departments_list"))
