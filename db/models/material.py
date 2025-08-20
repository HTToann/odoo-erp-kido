from configs import db
from sqlalchemy.dialects.postgresql import JSONB


class Material(db.Model):
    __tablename__ = "material"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sku = db.Column(db.String(60), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))

    unit_id = db.Column(db.Integer, db.ForeignKey("unit.id"), nullable=False)
    unit = db.relationship("Unit", backref="materials")

    attrs = db.Column(JSONB, default=dict)
    is_active = db.Column(db.Boolean, default=True)
