from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import qc as qc_dao, goods_receipt as gr_dao

qc_bp = Blueprint("qc_web", __name__)


@qc_bp.route("/qcs")
@login_required
def qc_list():
    qcs = qc_dao.list_qcs()
    return render_template("qc/qc.html", qcs=qcs)


@qc_bp.route("/qcs/add", methods=["GET", "POST"])
@login_required
def qc_add():
    if request.method == "POST":
        gr_id = request.form.get("gr_id")
        status = request.form.get("status", "pending")
        lines = _extract_lines(request)  # gr_line_id, result, note
        qc_dao.create_qc(gr_id, status, lines)
        flash("Tạo QC Report thành công", "success")
        return redirect(url_for("qc_web.qc_list"))
    grs = gr_dao.list_grs()
    gr_lines = qc_dao.list_all_gr_lines()
    return render_template(
        "qc/qc_form.html", action="add", qc=None, grs=grs, gr_lines=gr_lines
    )


@qc_bp.route("/qcs/edit/<int:qc_id>", methods=["GET", "POST"])
@login_required
def qc_edit(qc_id: int):
    try:
        qc = qc_dao.get_qc(qc_id)
        if not qc:
            flash("Không tìm thấy QC", "warning")
            return redirect(url_for("qc_web.qc_list"))

        if request.method == "POST":
            # nếu muốn cho đổi GR khi sửa thì lấy từ form:
            gr_id = request.form.get("gr_id") or qc.gr_id
            status = request.form.get("status", "pending")
            lines = _extract_lines(request)
            action = request.form.get("action")  # 'save' | 'finalize'

            try:
                if action == "finalize":
                    # chốt & nhập kho
                    qc_dao.finalize_qc(qc_id, status, lines)
                    flash("Đã CHỐT QC và nhập kho phần đạt.", "success")
                else:
                    # chỉ lưu (không ghi kho)
                    qc_dao.update_qc(qc_id, gr_id, status, lines)
                    flash("Đã lưu QC.", "success")
            except Exception as ex:
                flash(str(ex), "danger")

            return redirect(url_for("qc_web.qc_list"))
    except Exception as e:
        return redirect(url_for("qc_web.qc_list"))

    # GET
    grs = gr_dao.list_grs()  # 👈 thêm dòng này
    gr_lines = qc_dao.list_all_gr_lines()
    return render_template(
        "qc/qc_form.html",
        qc=qc,
        grs=grs,  # 👈 và truyền vào template
        gr_lines=gr_lines,
        action="edit",
    )


def _extract_lines(req):
    lines = []
    # form keys: lines[i][gr_line_id], lines[i][result], lines[i][accepted_qty], lines[i][note]
    idxs = set()
    for k in req.form:
        if k.startswith("lines[") and "][gr_line_id]" in k:
            idxs.add(k.split("[")[1].split("]")[0])
    for i in idxs:
        gr_line_id = req.form.get(f"lines[{i}][gr_line_id]")
        result = req.form.get(f"lines[{i}][result]")
        note = req.form.get(f"lines[{i}][note]")
        acc = req.form.get(f"lines[{i}][accepted_qty]")
        if gr_line_id:
            lines.append(
                {
                    "gr_line_id": int(gr_line_id),
                    "result": (result or "pass"),
                    "note": note,
                    "accepted_qty": (
                        float(acc)
                        if acc
                        not in (
                            None,
                            "",
                        )
                        else None
                    ),
                }
            )
    return lines


@qc_bp.route("/qcs/delete/<int:qc_id>", methods=["POST"])
@login_required
def qc_delete(qc_id: int):
    try:
        qc_dao.delete_qc(qc_id)
        flash("Xóa QC thành công", "success")
        return redirect(url_for("qc_web.qc_list"))
    except Exception as e:
        # flash("Không thể xóa QC.", "danger")
        return redirect(url_for("qc_web.qc_list"))
