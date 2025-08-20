from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from dao import goods_receipt as gr_dao, purchase as po_dao, material as material_dao
from sqlalchemy import func
from db.models.purchase import POStatus

gr_bp = Blueprint("gr_web", __name__)


@gr_bp.route("/goods-receipts")
@login_required
def gr_list():
    goods_receipts = gr_dao.list_grs()
    return render_template("receipt/goods_receipt.html", goods_receipts=goods_receipts)


@gr_bp.route("/goods-receipts/api/po/<int:po_id>/remaining")
@login_required
def gr_api_po_remaining(po_id: int):
    po = po_dao.get_po(po_id)
    # chỉ cho PO đã CONFIRMED
    po_is_confirmed = (po.status == POStatus.CONFIRMED) or (
        getattr(po.status, "value", None) == "CONFIRMED"
    )
    if not po or not po_is_confirmed:
        return jsonify([])
    rows = po_dao.po_lines_with_remaining(po_id)
    mats = {m.id: m for m in material_dao.list_materials()}

    payload = []
    for r in rows:
        if r["remaining"] <= 0:
            continue
        m = mats.get(r["material_id"])
        payload.append(
            {
                "po_line_id": r["po_line_id"],
                "material_id": r["material_id"],
                "sku": m.sku if m else "",
                "name": m.name if m else "",
                "remaining": r["remaining"],
            }
        )
    return jsonify(payload)


@gr_bp.route("/goods-receipts/add", methods=["GET", "POST"])
@login_required
def gr_add():
    if request.method == "POST":
        try:
            po_id = request.form.get("po_id")
            status = request.form.get("status", "draft")
            lines = _extract_lines(request)  # nhớ chứa po_line_id nếu có
            gr_dao.create_gr(po_id, status, lines)
            flash("Tạo GR thành công", "success")
            return redirect(url_for("gr_web.gr_list"))
        except ValueError as e:
            flash(str(e), "warning")

    return render_template(
        "receipt/goods_receipt_form.html",
        action="add",
        gr=None,
        purchases=po_dao.list_purchases_confirmed(),
        materials=material_dao.list_materials(),
    )


@gr_bp.route("/goods-receipts/from-po/<int:po_id>")
@login_required
def gr_from_po(po_id: int):
    po = po_dao.get_po(po_id)
    if not po:
        flash("Không tìm thấy PO", "warning")
        return redirect(url_for("gr_web.gr_add"))
    if str(po.status).endswith("CONFIRMED") is False:
        flash("PO chưa CONFIRMED, không thể nhận hàng.", "warning")
        return redirect(url_for("gr_web.gr_add"))

    remain = po_dao.po_lines_with_remaining(po.id)  # dùng DAO ở trên
    # Chỉ prefill những dòng còn lại > 0
    prefill = [
        {
            "material_id": r["material_id"],
            "qty": r["remaining"],
            "po_line_id": r["po_line_id"],
        }
        for r in remain
        if r["remaining"] > 0
    ]

    return render_template(
        "receipt/goods_receipt_form.html",
        action="add",
        gr=None,
        purchases=po_dao.list_purchases_confirmed(),
        materials=material_dao.list_materials(),
        prefill_lines=prefill,
        preselected_po_id=po.id,
    )


@gr_bp.route("/goods-receipts/edit/<int:gr_id>", methods=["GET", "POST"])
@login_required
def gr_edit(gr_id: int):
    gr = gr_dao.get_gr(gr_id)
    if not gr:
        flash("Không tìm thấy GR", "warning")
        return redirect(url_for("gr.gr_list"))
    if request.method == "POST":
        try:
            po_id = request.form.get("po_id")
            status = request.form.get("status", "draft")
            lines = _extract_lines(request)
            gr_dao.update_gr(gr_id, po_id, status, lines)
            flash("Cập nhật GR thành công", "success")
            return redirect(url_for("gr_web.gr_list"))
        except ValueError as e:
            flash(str(e), "warning")
    purchases = po_dao.list_purchases()
    materials = material_dao.list_materials()
    return render_template(
        "receipt/goods_receipt_form.html",
        action="edit",
        gr=gr,
        purchases=purchases,
        materials=materials,
    )


@gr_bp.route("/goods-receipts/delete/<int:gr_id>", methods=["POST"])
@login_required
def gr_delete(gr_id: int):
    gr_dao.delete_gr(gr_id)
    flash("Xóa GR thành công", "success")
    return redirect(url_for("gr_web.gr_list"))


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
