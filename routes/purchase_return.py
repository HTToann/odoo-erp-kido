from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import purchase_return as ret_dao, goods_receipt as gr_dao, qc as qc_dao

preturn_bp = Blueprint("preturn_web", __name__)


@preturn_bp.route("/returns")
@login_required
def return_list():
    returns = ret_dao.list_returns()
    return render_template("purchase/purchase_return.html", returns=returns)


@preturn_bp.route("/returns/add", methods=["GET", "POST"])
@login_required
def return_add():
    if request.method == "POST":
        gr_id = request.form.get("gr_id")
        status = request.form.get("status", "draft")
        lines = _extract_lines(request)
        action = request.form.get("action")  # 'save' or 'finalize'
        # nếu bấm "Chốt & Ghi kho" thì ép status='posted'
        if action == "finalize":
            status = "posted"
        try:
            ret_dao.create_return(gr_id, status, lines)
            flash("Tạo phiếu trả hàng thành công", "success")
        except Exception as ex:
            flash(str(ex), "danger")
        return redirect(url_for("preturn_web.return_list"))
    grs = gr_dao.list_grs()
    gr_lines = qc_dao.list_all_gr_lines()
    return render_template(
        "purchase/purchase_return_form.html",
        action="add",
        ret=None,
        grs=grs,
        gr_lines=gr_lines,
    )


@preturn_bp.route("/returns/edit/<int:return_id>", methods=["GET", "POST"])
@login_required
def return_edit(return_id: int):
    ret = ret_dao.get_return(return_id)
    if not ret:
        flash("Không tìm thấy phiếu trả hàng", "warning")
        return redirect(url_for("preturn_web.return_list"))
    if request.method == "POST":
        gr_id = request.form.get("gr_id")
        status = request.form.get("status", "draft")
        lines = _extract_lines(request)
        action = request.form.get("action")
        if action == "finalize":
            status = "posted"
        try:
            ret_dao.update_return(return_id, gr_id, status, lines)
            flash("Cập nhật phiếu trả hàng thành công", "success")
        except Exception as ex:
            flash(str(ex), "danger")
        return redirect(url_for("preturn_web.return_list"))
    grs = gr_dao.list_grs()
    gr_lines = qc_dao.list_all_gr_lines()
    return render_template(
        "purchase/purchase_return_form.html",
        action="edit",
        ret=ret,
        grs=grs,
        gr_lines=gr_lines,
    )


@preturn_bp.route("/returns/delete/<int:return_id>", methods=["POST"])
@login_required
def return_delete(return_id: int):
    ret_dao.delete_return(return_id)
    flash("Xóa phiếu trả hàng thành công", "success")
    return redirect(url_for("preturn_web.return_list"))


def _extract_lines(req):
    lines = []
    for key in req.form:
        if key.startswith("lines[") and key.endswith("][gr_line_id]"):
            idx = key.split("[")[1].split("]")[0]
            gr_line_id = req.form.get(f"lines[{idx}][gr_line_id]")
            qty = req.form.get(f"lines[{idx}][qty]")
            reason = req.form.get(f"lines[{idx}][reason]")
            if gr_line_id and qty:
                lines.append(
                    {"gr_line_id": int(gr_line_id), "qty": float(qty), "reason": reason}
                )
    return lines
