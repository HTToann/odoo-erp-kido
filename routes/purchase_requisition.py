from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from db.models.user import UserRole
from db.models.purchase_requisition import PurchaseRequisitionStatus
from dao import (
    purchase_requisition as pr_dao,
    material as material_dao,
    department as department_dao,
)
from dao import user as user_dao  # viết dao/user.py trả về list users
from sqlalchemy.exc import SQLAlchemyError

pr_bp = Blueprint("pr_web", __name__)


@pr_bp.route("/prs")
@login_required
def pr_list():
    prs = pr_dao.list_prs()
    return render_template("purchase/purchase_requisition.html", requisitions=prs)


@pr_bp.route("/prs/add", methods=["GET", "POST"])
@login_required
def pr_add():
    if request.method == "POST":
        requester_id = request.form.get("requester_id")
        note = request.form.get("note")
        lines = _extract_lines(request)
        pr_dao.create_pr(requester_id, note, lines)
        flash("Tạo PR thành công", "success")
        return redirect(url_for("pr_web.pr_list"))
    users = user_dao.list_users()
    mats = material_dao.list_materials()
    return render_template(
        "purchase/purchase_requisition_form.html",
        action="add",
        users=users,
        materials=mats,
    )


@pr_bp.route("/prs/edit/<int:pr_id>", methods=["GET", "POST"])
@login_required
def pr_edit(pr_id: int):
    pr = pr_dao.get_pr(pr_id)
    if not pr:
        flash("Không tìm thấy PR", "warning")
        return redirect(url_for("pr_web.pr_list"))

    if request.method == "POST":
        requester_id = request.form.get("requester_id")
        note = request.form.get("note")
        status = (request.form.get("status") or "DRAFT").upper()
        lines = _extract_lines(request)

        is_approver = False
        try:
            is_approver = current_user.has_role("APPROVER") or current_user.has_role(
                UserRole.APPROVER
            )
        except Exception:
            is_approver = current_user.has_role("APPROVER")

        if not is_approver:
            status = pr.status.value if getattr(pr, "status", None) else "DRAFT"

        try:
            pr_dao.update_pr(pr_id, requester_id, note, status, lines)
            flash("Cập nhật PR thành công", "success")
            return redirect(url_for("pr_web.pr_list"))
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for("pr_web.pr_edit", pr_id=pr_id))
        except SQLAlchemyError:
            flash("Có lỗi khi lưu dữ liệu. Vui lòng thử lại.", "danger")
            return redirect(url_for("pr_web.pr_edit", pr_id=pr_id))

    users = user_dao.list_users()
    mats = material_dao.list_materials()
    return render_template(
        "purchase/purchase_requisition_form.html",
        action="edit",
        pr=pr,
        users=users,
        materials=mats,
        PurchaseRequisitionStatus=PurchaseRequisitionStatus,
        UserRole=UserRole,
        can_edit_status=current_user.has_role("APPROVER"),
    )


@pr_bp.route("/prs/delete/<int:pr_id>", methods=["POST"])
@login_required
def pr_delete(pr_id: int):
    pr_dao.delete_pr(pr_id)
    flash("Xóa PR thành công", "success")
    return redirect(url_for("pr_web.pr_list"))


def _extract_lines(req):
    # nhận lines[i][material_id], lines[i][qty]
    lines = []
    for key in req.form:
        # chỉ lấy theo index của material_id
        if key.startswith("lines[") and key.endswith("][material_id]"):
            idx = key.split("[")[1].split("]")[0]
            material_id = req.form.get(f"lines[{idx}][material_id]")
            qty = req.form.get(f"lines[{idx}][qty]")
            if material_id and qty:
                lines.append({"material_id": int(material_id), "qty": float(qty)})
    return lines
