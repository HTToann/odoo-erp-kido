from configs import db
from werkzeug.security import generate_password_hash
from db.models.user import User, UserRole
from app import app  # lấy app để chạy context

with app.app_context():
    # Xóa toàn bộ user cũ (nếu muốn reset dữ liệu seed)

    users = [
        User(
            username="admin",
            password_hash=generate_password_hash("1"),
            full_name="System Admin",
            role=UserRole.ADMIN,
            is_active=True,
        ),
        User(
            username="buyer1",
            password_hash=generate_password_hash("1"),
            full_name="Purchasing Buyer",
            role=UserRole.BUYER,
            is_active=True,
        ),
        User(
            username="approver1",
            password_hash=generate_password_hash("1"),
            full_name="Purchase Approver",
            role=UserRole.APPROVER,
            is_active=True,
        ),
        User(
            username="warehouse1",
            password_hash=generate_password_hash("1"),
            full_name="Warehouse Staff",
            role=UserRole.WAREHOUSE,
            is_active=True,
        ),
        User(
            username="qc1",
            password_hash=generate_password_hash("1"),
            full_name="Quality Control",
            role=UserRole.QC,
            is_active=True,
        ),
        User(
            username="accountant1",
            password_hash=generate_password_hash("1"),
            full_name="Finance Accountant",
            role=UserRole.ACCOUNTANT,
            is_active=True,
        ),
    ]

    db.session.add_all(users)
    db.session.commit()

    print("✅ Seeded users with all defined roles")
