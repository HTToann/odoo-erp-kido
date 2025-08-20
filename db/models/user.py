# db/models/user.py
import enum
from configs import db
from flask_login import UserMixin


class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    BUYER = "BUYER"  # Người mua hàng (PO)
    APPROVER = "APPROVER"  # Người duyệt
    WAREHOUSE = "WAREHOUSE"  # Thủ kho (GR)
    QC = "QC"  # Kiểm tra chất lượng
    ACCOUNTANT = "ACCOUNTANT"  # Kế toán


class User(db.Model, UserMixin):
    __tablename__ = "user_account"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.BUYER, nullable=False)

    def get_id(self):
        return str(self.id)

    def has_role(self, *roles: UserRole):
        """Kiểm tra xem user có 1 trong các role truyền vào"""
        return self.role in roles
