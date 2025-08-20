# routes/rfq.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import rfq as rfq_dao, material as material_dao, purchase_requisition as pr_dao
from dao import purchase_requisition as pr_dao  # ở đầu file

rfq_bp = Blueprint("rfq_web", __name__)


@rfq_bp.route("/rfqs")
@login_required
def rfq_list():
    rfqs = rfq_dao.list_rfqs()
    prs = pr_dao.list_prs_approved()  # hoặc list_prs(), tuỳ bạn
    return render_template("rfq/rfq.html", rfqs=rfqs, prs=prs)


@rfq_bp.route("/rfqs/from-pr/<int:pr_id>")
@login_required
def rfq_from_pr(pr_id: int):
    # mở form add và truyền from_pr để prefill
    return redirect(url_for("rfq_web.rfq_add", from_pr=pr_id))


@rfq_bp.route("/rfqs/add", methods=["GET", "POST"])
@login_required
def rfq_add():
    if request.method == "POST":
        pr_id = request.form.get("pr_id")
        if not pr_id:
            flash("Bạn phải chọn một PR trước khi tạo RFQ", "danger")
            return redirect(url_for("rfq_web.rfq_add"))
        status = request.form.get("status", "draft")
        lines = _extract_lines(request)
        rfq_dao.create_rfq(pr_id, status, lines)
        flash("Tạo RFQ thành công", "success")
        return redirect(url_for("rfq_web.rfq_list"))

    # GET
    from_pr = request.args.get("from_pr")
    prefill_lines = []
    if from_pr:
        pr = pr_dao.get_pr(int(from_pr))
        if pr and pr.lines:
            for ln in pr.lines:
                prefill_lines.append(
                    {
                        "material_id": ln.material_id,
                        "qty": float(ln.qty or 0),
                    }
                )

    prs = pr_dao.list_prs_approved()  # hoặc list_prs(), tuỳ bạn
    mats = material_dao.list_materials()
    return render_template(
        "rfq/rfq_form.html",
        action="add",
        prs=prs,
        materials=mats,
        rfq=None,
        prefill_lines=prefill_lines,  # 👈 truyền sang template
    )


# @rfq_bp.route("/rfqs/from-pr/<int:pr_id>")
# @login_required
# def rfq_from_pr(pr_id: int):
#     """Mở form RFQ và tự động đổ dòng từ PR."""
#     pr = pr_dao.get_pr(pr_id)
#     if not pr:
#         flash("Không tìm thấy PR", "warning")
#         return redirect(url_for("rfq_web.rfq_list"))
#     prefill = [{"material_id": ln.material_id, "qty": float(ln.qty)} for ln in pr.lines]
#     return render_template(
#         "rfq/rfq_form.html",
#         action="add",
#         prs=pr_dao.list_prs(),
#         materials=material_dao.list_materials(),
#         prefill_lines=prefill,
#         preselected_pr_id=pr.id,
#         rfq=None,
#     )


@rfq_bp.route("/rfqs/edit/<int:rfq_id>", methods=["GET", "POST"])
@login_required
def rfq_edit(rfq_id: int):
    rfq = rfq_dao.get_rfq(rfq_id)
    if not rfq:
        flash("Không tìm thấy RFQ", "warning")
        return redirect(url_for("rfq_web.rfq_list"))
    if request.method == "POST":
        pr_id = request.form.get("pr_id")
        status = request.form.get("status", "draft")
        lines = _extract_lines(request)
        rfq_dao.update_rfq(rfq_id, pr_id, status, lines)
        flash("Cập nhật RFQ thành công", "success")
        return redirect(url_for("rfq_web.rfq_list"))
    prs = pr_dao.list_prs()
    mats = material_dao.list_materials()
    return render_template(
        "rfq/rfq_form.html", action="edit", rfq=rfq, prs=prs, materials=mats
    )


@rfq_bp.route("/rfqs/delete/<int:rfq_id>", methods=["POST"])
@login_required
def rfq_delete(rfq_id: int):
    rfq_dao.delete_rfq(rfq_id)
    flash("Xóa RFQ thành công", "success")
    return redirect(url_for("rfq_web.rfq_list"))


def _extract_lines(req):
    lines = []
    for key in req.form:
        if key.startswith("lines[") and key.endswith("][material_id]"):
            idx = key.split("[")[1].split("]")[0]
            material_id = req.form.get(f"lines[{idx}][material_id]")
            qty = req.form.get(f"lines[{idx}][qty]")
            if material_id and qty:
                lines.append({"material_id": int(material_id), "qty": float(qty)})
    return lines
