# routes/vendor_quotation.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import (
    vendor_quotation as vq_dao,
    rfq as rfq_dao,
    supplier as supplier_dao,
    material as material_dao,
)

vq_bp = Blueprint("vq_web", __name__)


@vq_bp.route("/vqs")
@login_required
def vq_list():
    vqs = vq_dao.list_vqs()
    return render_template("vendor/vendor_quotation.html", vqs=vqs)


@vq_bp.route("/vqs/add", methods=["GET", "POST"])
@login_required
def vq_add():
    """Form tạo VQ trống (hoặc prefill với ?from_rfq=<id>)."""
    from_rfq = request.args.get("from_rfq")
    prefill_lines = None
    preselected_rfq_id = None
    if from_rfq:
        rfq = rfq_dao.get_rfq(int(from_rfq))
        if rfq and rfq.lines:
            prefill_lines = [
                {"material_id": ln.material_id, "qty": float(ln.qty), "price": 0}
                for ln in rfq.lines
            ]
            preselected_rfq_id = rfq.id

    if request.method == "POST":
        rfq_id = request.form.get("rfq_id")
        supplier_id = request.form.get("supplier_id")
        status = request.form.get("status", "received")
        lines = _extract_lines(request)
        vq_dao.create_vq(rfq_id, supplier_id, status, lines)
        flash("Nhập báo giá thành công", "success")
        return redirect(url_for("vq_web.vq_list"))

    rfqs = rfq_dao.list_rfqs()
    suppliers = supplier_dao.list_suppliers()
    mats = material_dao.list_materials()

    return render_template(
        "vendor/vendor_quotation_form.html",
        action="add",
        rfqs=rfqs,
        suppliers=suppliers,
        materials=mats,
        vq=None,
        prefill_lines=prefill_lines,
        preselected_rfq_id=preselected_rfq_id,
    )


@vq_bp.route("/vqs/from-rfq/<int:rfq_id>")
@login_required
def vq_from_rfq(rfq_id: int):
    rfq = rfq_dao.get_rfq(rfq_id)
    if not rfq:
        flash("Không tìm thấy RFQ", "warning")
        return redirect(url_for("vq_web.vq_list"))
    prefill = [
        {"material_id": ln.material_id, "qty": float(ln.qty), "price": 0}
        for ln in rfq.lines
    ]
    return render_template(
        "vendor/vendor_quotation_form.html",
        action="add",
        rfqs=rfq_dao.list_rfqs(),
        suppliers=supplier_dao.list_suppliers(),
        materials=material_dao.list_materials(),
        prefill_lines=prefill,
        preselected_rfq_id=rfq.id,
        vq=None,
    )


@vq_bp.route("/vqs/edit/<int:vq_id>", methods=["GET", "POST"])
@login_required
def vq_edit(vq_id: int):
    vq = vq_dao.get_vq(vq_id)
    if not vq:
        flash("Không tìm thấy báo giá", "warning")
        return redirect(url_for("vq_web.vq_list"))

    if request.method == "POST":
        rfq_id = request.form.get("rfq_id")
        supplier_id = request.form.get("supplier_id")
        status = request.form.get("status", "received")
        lines = _extract_lines(request)
        vq_dao.update_vq(vq_id, rfq_id, supplier_id, status, lines)
        flash("Cập nhật báo giá thành công", "success")
        return redirect(url_for("vq_web.vq_list"))

    rfqs = rfq_dao.list_rfqs()
    suppliers = supplier_dao.list_suppliers()
    mats = material_dao.list_materials()
    return render_template(
        "vendor/vendor_quotation_form.html",
        action="edit",
        vq=vq,
        rfqs=rfqs,
        suppliers=suppliers,
        materials=mats,
    )


@vq_bp.route("/vqs/delete/<int:vq_id>", methods=["POST"])
@login_required
def vq_delete(vq_id: int):
    vq_dao.delete_vq(vq_id)
    flash("Xóa báo giá thành công", "success")
    return redirect(url_for("vq_web.vq_list"))


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
