from configs import db


class Unit(db.Model):
    __tablename__ = "unit"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # int tự tăng
    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    base_factor = db.Column(db.Numeric(18, 6), default=1)
