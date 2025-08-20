from index import main_bp
from routes.auth import auth_bp
from routes.supplier import supplier_bp
from routes.unit import unit_bp
from routes.material import material_bp
from routes.department import department_bp
from routes.purchase_requisition import pr_bp
from routes.rfq import rfq_bp
from routes.vendor_quotation import vq_bp
from routes.purchases import purchase_bp
from routes.goods_receipt import gr_bp
from routes.qc import qc_bp
from routes.invoice import invoice_bp
from routes.payment import payment_bp
from routes.purchase_return import preturn_bp


def blue_print(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(supplier_bp)
    app.register_blueprint(unit_bp)
    app.register_blueprint(material_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(pr_bp)
    app.register_blueprint(rfq_bp)
    app.register_blueprint(vq_bp)
    app.register_blueprint(purchase_bp)
    app.register_blueprint(gr_bp)
    app.register_blueprint(qc_bp)
    app.register_blueprint(invoice_bp)
    app.register_blueprint(payment_bp)
    app.register_blueprint(preturn_bp)
