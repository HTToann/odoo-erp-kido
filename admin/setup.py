# admin/setup.py
from flask import redirect, url_for, request, flash
from flask_login import current_user, logout_user
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.menu import MenuLink
from configs import db
from db.models.user import UserRole


# Chặn truy cập nếu không phải admin


class MyAdminIndex(AdminIndexView):
    @expose("/")
    def index(self):
        # Chưa đăng nhập -> đưa về trang login (KHÔNG flash lỗi)
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))

        # Đăng nhập rồi nhưng không phải ADMIN -> flash lỗi
        if not current_user.has_role(UserRole.ADMIN):
            flash("Bạn không có quyền truy cập vào trang quản trị.", "danger")
            return redirect(url_for("auth.login"))

        return super().index()

    @expose("/logout")
    def admin_logout(self):
        if current_user.is_authenticated:
            logout_user()
            flash("Đăng xuất thành công.", "success")
        # Giữ yêu cầu: quay về /manage (admin.index)
        return redirect(url_for("admin.index"))

    def is_accessible(self):
        return current_user.is_authenticated and current_user.has_role(UserRole.ADMIN)

    def inaccessible_callback(self, name, **kwargs):
        # Chưa đăng nhập: không flash, chỉ chuyển tới login (giữ next)
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.url))

        # Đã đăng nhập nhưng sai role: báo lỗi rồi chuyển
        flash("Bạn không có quyền truy cập vào trang quản trị.", "danger")
        return redirect(url_for("auth.login"))


class SecureModelView(ModelView):
    can_view_details = True
    can_export = True

    def is_accessible(self):
        return current_user.is_authenticated and current_user.has_role(UserRole.ADMIN)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login", next=request.url))


# Ví dụ tuỳ biến cho một model cụ thể
class PurchaseOrderView(SecureModelView):
    column_searchable_list = ["po_no"]
    column_filters = ["status", "order_date", "supplier_id"]
    column_list = ["id", "po_no", "supplier", "order_date", "status", "total"]
    form_columns = [
        "po_no",
        "supplier",
        "order_date",
        "expected_date",
        "status",
        "subtotal",
        "tax",
        "total",
    ]


def init_admin(app):

    admin = Admin(
        app,
        name="ERP Admin",
        template_mode="bootstrap4",
        index_view=MyAdminIndex(url="/manage"),  # index sẽ là /manage/
        url="/manage",  # toàn bộ admin ở /manage
    )
    # Import model ở đây để tránh circular import
    from db.models.user import User
    from db.models.material import Material
    from db.models.unit import Unit
    from db.models.supplier import Supplier
    from db.models.department import Department
    from db.models.purchase_requisition import PurchaseRequisition, PRLine
    from db.models.rfq import RFQ, RFQLine
    from db.models.vendor_quotation import VendorQuotation, VendorQuotationLine
    from db.models.purchase import PurchaseOrder, PurchaseOrderItem
    from db.models.goods_receipt import GoodsReceipt, GRLine
    from db.models.qc import QCLine, QCReport
    from db.models.purchase_return import PurchaseReturn, ReturnLine
    from db.models.invoice_payment import VendorInvoice, InvoiceLine, Payment
    from db.models.inventory import StockItem, StockMovement

    # from db.models.rfq import RFQ
    # from db.models.vendor_quotation import VendorQuotation
    # ... tuỳ bạn

    admin.add_view(
        SecureModelView(
            User,
            db.session,
            category="System",
            endpoint="admin_user",
            name="Users",
        )
    )
    admin.add_view(
        SecureModelView(
            Unit,
            db.session,
            category="Master Data",
            endpoint="admin_unit",
            name="Units",
        )
    )
    admin.add_view(
        SecureModelView(
            Material,
            db.session,
            category="Master Data",
            endpoint="admin_material",
            name="Materials",
        )
    )

    admin.add_view(
        SecureModelView(
            Supplier,
            db.session,
            category="Master Data",
            endpoint="admin_supplier",
            name="Suppliers",
        )
    )

    admin.add_view(
        SecureModelView(
            PurchaseRequisition,
            db.session,
            category="PR - Yêu cầu mua hàng",
            endpoint="admin_pr",
            name="Purchase Requisitions",
        )
    )
    admin.add_view(
        SecureModelView(
            PRLine,
            db.session,
            category="PR - Yêu cầu mua hàng",
            endpoint="admin_prline",
            name="PR Lines",
        )
    )
    admin.add_view(
        SecureModelView(
            RFQ,
            db.session,
            category="RFQ - Yêu cầu báo giá",
            endpoint="admin_rfq",
            name="RFQs",
        )
    )
    admin.add_view(
        SecureModelView(
            RFQLine,
            db.session,
            category="RFQ - Yêu cầu báo giá",
            endpoint="admin_rfq_lines",
            name="RFQ Lines",
        )
    )

    admin.add_view(
        SecureModelView(
            VendorQuotation,
            db.session,
            category="VQ – Nhập & So sánh báo giá NCC",
            endpoint="admin_VQ",
            name="VQ",
        )
    )
    admin.add_view(
        SecureModelView(
            VendorQuotationLine,
            db.session,
            category="VQ – Nhập & So sánh báo giá NCC",
            endpoint="admin_VQLines",
            name="VQ Lines",
        )
    )

    admin.add_view(
        PurchaseOrderView(
            PurchaseOrder,
            db.session,
            category="PO - Đơn Mua",
            endpoint="admin_po",
            name="Purchase Orders",
        )
    )
    admin.add_view(
        SecureModelView(
            PurchaseOrderItem,
            db.session,
            category="PO - Đơn Mua",
            endpoint="admin_poitems",
            name="Purchase Orders Items",
        )
    )

    admin.add_view(
        SecureModelView(
            GoodsReceipt,
            db.session,
            category="GR - Nhận hàng",
            endpoint="admin_gr",
            name="Goods Receipts",
        )
    )
    admin.add_view(
        SecureModelView(
            GRLine,
            db.session,
            category="GR - Nhận hàng",
            endpoint="admin_grlines",
            name="GR Lines",
        )
    )
    admin.add_view(
        SecureModelView(
            QCReport,
            db.session,
            category="QC - Kiểm tra chất lượng",
            endpoint="admin_qc_report",
            name="QC Reports",
        )
    )
    admin.add_view(
        SecureModelView(
            QCLine,
            db.session,
            category="QC - Kiểm tra chất lượng",
            endpoint="admin_qc_line",
            name="QC Lines",
        )
    )
    admin.add_view(
        SecureModelView(
            PurchaseReturn,
            db.session,
            category="Return - Trả hàng",
            endpoint="admin_return",
            name="Purchase Returns",
        )
    )
    admin.add_view(
        SecureModelView(
            ReturnLine,
            db.session,
            category="Return - Trả hàng",
            endpoint="admin_return_line",
            name="Purchase Returns Lines",
        )
    )
    admin.add_view(
        SecureModelView(
            StockItem,
            db.session,
            category="Inventory - Kho",
            endpoint="admin_stock_item",
            name="Stock Items",
        )
    )
    admin.add_view(
        SecureModelView(
            StockMovement,
            db.session,
            category="Inventory - Kho",
            endpoint="admin_stock_movement",
            name="Stock Movements",
        )
    )
    admin.add_link(
        MenuLink(
            name="Logout",
            category="System",
            endpoint="admin.admin_logout",  # <-- dùng endpoint thay vì url=url_for(...)
            icon_type="glyph",
            icon_value="glyphicon-log-out",
        )
    )
    # admin.add_view(
    #     SecureModelView(
    #         VendorInvoice,
    #         db.session,
    #         category="Finance",
    #         endpoint="admin_invoice",
    #         name="Invoices",
    #     )
    # )
    # admin.add_view(
    #     SecureModelView(
    #         InvoiceLine,
    #         db.session,
    #         category="Finance",
    #         endpoint="admin_invoice_line",
    #         name="Invoice Lines",
    #     )
    # )
    # admin.add_view(
    #     SecureModelView(
    #         Payment,
    #         db.session,
    #         category="Finance",
    #         endpoint="admin_payment",
    #         name="Payments",
    #     )
    # )

    return admin
