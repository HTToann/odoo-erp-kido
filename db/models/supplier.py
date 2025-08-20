from configs import db


class Supplier(db.Model):
    __tablename__ = "supplier"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # 👈 int tự tăng
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)

    phone = db.Column(db.String(30))
    email = db.Column(db.String(255))
    address = db.Column(db.Text)

    is_active = db.Column(db.Boolean, default=True)
