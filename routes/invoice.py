# routes/invoice.py (refactor)
from decimal import Decimal, InvalidOperation
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from dao import (
    invoice as inv_dao,
    supplier as supplier_dao,
    purchase as po_dao,
    material as material_dao,
)
from db.models.supplier import Supplier
from db.models.purchase import PurchaseOrderItem, PurchaseOrder
from db.models.material import Material
from db.models.goods_receipt import GoodsReceipt, GRLine
from configs import db

invoice_bp = Blueprint("invoice_web", __name__)


# ---------------- helpers ----------------
def _form_deps():
    return {
        "suppliers": supplier_dao.list_suppliers(),
        "purchases": po_dao.list_purchases(),
        "materials": material_dao.list_materials(),
    }


def _to_decimal(v, default="0"):
    try:
        return Decimal(
            str(
                v
                if v
                not in (
                    None,
                    "",
                )
                else default
            )
        )
    except InvalidOperation:
        return Decimal(default)


def _extract_lines(req):
    """Đọc lines[i][material_id|qty|price] -> list[dict]. Lọc dòng trống."""
    lines = []
    idxs = set()
    for k in req.form:
        if k.startswith("lines[") and k.endswith("][material_id]"):
            idxs.add(k.split("[")[1].split("]")[0])

    for i in idxs:
        material_id = req.form.get(f"lines[{i}][material_id]")
        qty = _to_decimal(req.form.get(f"lines[{i}][qty]"))
        price = _to_decimal(req.form.get(f"lines[{i}][price]"))
        if material_id and qty is not None and price is not None:
            lines.append(
                {
                    "material_id": int(material_id),
                    "qty": float(qty),  # DAO hiện tại nhận float/Decimal đều OK
                    "price": float(price),
                }
            )
    # loại dòng không có material hoặc qty<=0
    lines = [ln for ln in lines if ln["material_id"] and ln["qty"] > 0]
    return lines


# ---------------- routes ----------------
@invoice_bp.route("/invoices/api/po/<int:po_id>/supplier")
@login_required
def invoice_api_po_supplier(po_id: int):
    po = db.session.get(PurchaseOrder, po_id)
    if not po:
        return jsonify({}), 404
    sup = db.session.get(Supplier, po.supplier_id) if po.supplier_id else None
    return jsonify({"supplier_id": po.supplier_id, "name": (sup.name if sup else "")})


@invoice_bp.route("/invoices")
@login_required
def invoice_list():
    invoices = inv_dao.list_invoices()
    return render_template("invoice/invoice_payment.html", invoices=invoices)


@invoice_bp.route("/invoices/add", methods=["GET", "POST"])
@login_required
def invoice_add():
    if request.method == "POST":
        supplier_id = request.form.get("supplier_id") or request.form.get(
            "supplier_id_hidden"
        )
        po_id = request.form.get("po_id") or None
        status = request.form.get("status", "draft")
        issued_at = request.form.get("issued_at")  # 'YYYY-MM-DD' hoặc ''
        lines = _extract_lines(request)
        # nếu có PO -> supplier phải khớp

        if po_id:
            po = PurchaseOrder.query.get(int(po_id))
            if not po:
                flash("PO không tồn tại.", "danger")
                return redirect(url_for("invoice_web.invoice_add"))
            if str(po.supplier_id) != str(supplier_id):
                print(po.supplier_id, supplier_id)
                flash("Nhà cung cấp không khớp với PO đã chọn.", "danger")
                return redirect(url_for("invoice_web.invoice_add"))
        if not supplier_id:
            flash("Vui lòng chọn nhà cung cấp.", "warning")
        elif not lines:
            flash("Hóa đơn cần ít nhất một dòng hợp lệ.", "warning")
        else:
            try:
                inv_dao.create_invoice(
                    supplier_id, po_id, status, lines, issued_at=issued_at
                )
                flash("Tạo hóa đơn thành công", "success")
                return redirect(url_for("invoice_web.invoice_list"))
            except Exception as ex:
                flash(str(ex), "danger")

    deps = _form_deps()
    return render_template(
        "invoice/invoice_form.html",
        action="add",
        inv=None,
        **deps,
    )


@invoice_bp.route("/invoices/edit/<int:invoice_id>", methods=["GET", "POST"])
@login_required
def invoice_edit(invoice_id: int):
    inv = inv_dao.get_invoice(invoice_id)
    if not inv:
        flash("Không tìm thấy hóa đơn", "warning")
        return redirect(url_for("invoice_web.invoice_list"))

    if request.method == "POST":
        supplier_id = request.form.get("supplier_id") or request.form.get(
            "supplier_id_hidden"
        )
        po_id = request.form.get("po_id") or None
        status = request.form.get("status", "draft")
        issued_at = request.form.get("issued_at")
        lines = _extract_lines(request)
        try:
            inv_dao.update_invoice(
                invoice_id, supplier_id, po_id, status, lines, issued_at=issued_at
            )
            flash("Cập nhật hóa đơn thành công", "success")
            return redirect(url_for("invoice_web.invoice_list"))
        except Exception as ex:
            flash(str(ex), "danger")

    deps = _form_deps()
    return render_template(
        "invoice/invoice_form.html",
        action="edit",
        inv=inv,
        **deps,
    )


@invoice_bp.route("/invoices/delete/<int:invoice_id>", methods=["POST"])
@login_required
def invoice_delete(invoice_id: int):
    try:
        inv_dao.delete_invoice(invoice_id)
        flash("Xóa hóa đơn thành công", "success")
    except Exception as ex:
        flash(str(ex), "danger")
    return redirect(url_for("invoice_web.invoice_list"))


# --- API: lấy lines từ PO (PO Items) ---
@invoice_bp.route("/invoices/api/po/<int:po_id>/lines")
@login_required
def invoice_api_po_lines(po_id: int):
    po = PurchaseOrder.query.get(po_id)
    if not po:
        return jsonify([])

    # Lấy PO items + material
    rows = (
        db.session.query(PurchaseOrderItem, Material)
        .join(Material, Material.id == PurchaseOrderItem.material_id)
        .filter(PurchaseOrderItem.po_id == po_id)
        .all()
    )
    data = []
    for item, mat in rows:
        data.append(
            {
                "material_id": item.material_id,
                "sku": mat.sku or "",
                "name": mat.name or "",
                "qty": float(item.qty or 0),
                "price": float(item.price or 0) if hasattr(item, "price") else 0.0,
            }
        )
    return jsonify(data)


# --- API: lấy lines từ GR (GR Lines) + cố gắng map price theo PO Item ---
@invoice_bp.route("/invoices/api/gr/<int:gr_id>/lines")
@login_required
def invoice_api_gr_lines(gr_id: int):
    gr = GoodsReceipt.query.get(gr_id)
    if not gr:
        return jsonify([])

    # Lấy các GR line
    gls = (
        db.session.query(GRLine, Material)
        .join(Material, Material.id == GRLine.material_id)
        .filter(GRLine.gr_id == gr_id)
        .all()
    )

    # Chuẩn bị map giá từ PO Item theo material_id (nếu có)
    po_price_map = {}
    if gr.po_id:
        items = PurchaseOrderItem.query.filter_by(po_id=gr.po_id).all()
        for it in items:
            po_price_map[int(it.material_id)] = float(getattr(it, "price", 0) or 0)

    data = []
    for ln, mat in gls:
        price = po_price_map.get(int(ln.material_id), 0.0)
        data.append(
            {
                "material_id": ln.material_id,
                "sku": mat.sku or "",
                "name": mat.name or "",
                "qty": float(ln.qty or 0),
                "price": price,
            }
        )
    return jsonify(data)
