# routes/purchase.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from dao import purchase as po_dao, supplier as supplier_dao
from dao import vendor_quotation as vq_dao  # 👈 thêm để load VQ

purchase_bp = Blueprint("purchase_web", __name__)


@purchase_bp.route("/purchases")
@login_required
def purchases_list():
    purchases = po_dao.list_purchases()
    return render_template("purchase/purchases.html", purchases=purchases)


@purchase_bp.route("/purchases/add", methods=["GET", "POST"])
@login_required
def purchases_add():
    """
    Form tạo PO. Hỗ trợ query:
      - ?from_vq=<id> để prefill từ VQ
      - hoặc truyền sẵn supplier_id, totals...
    """
    from_vq = request.args.get("from_vq")

    prefill = {
        "supplier_id": None,
        "vq_id": None,
        "subtotal": 0,
        "tax": 0,
        "total": 0,
        "suggest_po_no": "",  # bạn có thể tự sinh mã
    }

    if from_vq:
        vq = vq_dao.get_vq(int(from_vq))
        if vq:
            prefill["vq_id"] = vq.id
            prefill["supplier_id"] = vq.supplier_id
            # tính tổng từ VQ lines:
            s = 0.0
            for ln in vq.lines or []:
                q = float(ln.qty or 0)
                p = float(ln.price or 0)
                s += q * p
            prefill["subtotal"] = round(s, 2)
            prefill["tax"] = 0
            prefill["total"] = round(s, 2)
            prefill["suggest_po_no"] = f"PO-VQ{vq.id}"

    if request.method == "POST":
        po_no = request.form.get("po_no", prefill["suggest_po_no"] or "")
        supplier_id = request.form.get("supplier_id")
        status = request.form.get("status", "draft")
        order_date = request.form.get("order_date")
        expected_date = request.form.get("expected_date")
        subtotal = request.form.get("subtotal", prefill["subtotal"])
        tax = request.form.get("tax", prefill["tax"])
        total = request.form.get("total", prefill["total"])
        vq_id = request.form.get("vq_id")  # hidden khi tạo từ VQ

        if vq_id:
            # ✅ Tạo PO từ VQ và sinh luôn PO Items

            # Nếu bạn có dropdown thuế %, chuyển ra tax_rate (0.08, 0.10 ...)
            tax_rate = None
            try:
                # ví dụ: nếu form gửi "tax_policy_rate" = "0.08"
                tax_rate = float(request.form.get("tax_policy_rate") or 0)
            except ValueError:
                tax_rate = None

            po = vq_dao.create_po_from_vq(
                int(vq_id),
                po_no,
                status=status,
                order_date=order_date,
                expected_date=expected_date,
                tax_rate=tax_rate if tax_rate else None,
                tax_amount=(float(tax) if tax else None),
            )
        else:
            # 🟨 Không đi từ VQ → tạo PO thuần như cũ (không sinh items)
            po_dao.create_po(
                po_no,
                supplier_id,
                status,
                order_date,
                expected_date,
                subtotal,
                tax,
                total,
                vq_id=None,  # đừng gửi vq_id sang nhánh này
            )

        flash("Tạo đơn mua hàng thành công", "success")
        return redirect(url_for("purchase_web.purchases_list"))

    suppliers = supplier_dao.list_suppliers()
    return render_template(
        "purchase/purchase_form.html",
        action="add",
        po=None,
        suppliers=suppliers,
        prefill=prefill,
    )


@purchase_bp.route("/purchases/from-vq/<int:vq_id>")
@login_required
def purchases_from_vq(vq_id: int):
    """Mở form PO, tự đổ dữ liệu từ VQ."""
    return redirect(url_for("purchase_web.purchases_add", from_vq=vq_id))


@purchase_bp.route("/purchases/edit/<int:po_id>", methods=["GET", "POST"])
@login_required
def purchases_edit(po_id: int):
    po = po_dao.get_po(po_id)
    if not po:
        flash("Không tìm thấy đơn mua hàng", "warning")
        return redirect(url_for("purchase_web.purchases_list"))

    if request.method == "POST":
        po_no = request.form.get("po_no", "")
        supplier_id = request.form.get("supplier_id")
        status = request.form.get("status", "draft")
        order_date = request.form.get("order_date")
        expected_date = request.form.get("expected_date")
        subtotal = request.form.get("subtotal", 0)
        tax = request.form.get("tax", 0)
        total = request.form.get("total", 0)
        vq_id = request.form.get("vq_id")  # hidden (giữ liên kết)

        po_dao.update_po(
            po_id,
            po_no,
            supplier_id,
            status,
            order_date,
            expected_date,
            subtotal,
            tax,
            total,
            vq_id=vq_id,
        )
        flash("Cập nhật đơn mua hàng thành công", "success")
        return redirect(url_for("purchase_web.purchases_list"))

    suppliers = supplier_dao.list_suppliers()
    return render_template(
        "purchase/purchase_form.html",
        action="edit",
        po=po,
        suppliers=suppliers,
        prefill=None,
    )


@purchase_bp.route("/purchases/delete/<int:po_id>", methods=["POST"])
@login_required
def purchases_delete(po_id: int):
    po_dao.delete_po(po_id)
    flash("Xóa đơn mua hàng thành công", "success")
    return redirect(url_for("purchase_web.purchases_list"))
