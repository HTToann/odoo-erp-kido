# seed/seed_units_materials.py
from configs import db
from db.models.unit import Unit
from db.models.material import Material
from db.models.supplier import Supplier
from app import app  # Flask app


# -------- Units --------
def seed_units():
    units = [
        ("KG", "Kilogram", 1),
        ("G", "Gram", 0.001),
        ("PCS", "Piece (cái)", 1),
        ("BOX10", "Hộp 10 cái", 10),
        ("PKG500G", "Gói 500g", 0.5),
        ("BOX20KG", "Thùng 20kg", 20),
    ]
    for code, name, factor in units:
        u = Unit.query.filter_by(code=code).first()
        if not u:
            db.session.add(Unit(code=code, name=name, base_factor=factor))
        else:
            # cập nhật nhẹ nếu đã tồn tại
            u.name = name
            u.base_factor = factor
    db.session.commit()
    print("✓ Units seeded/updated")


def get_unit_id(code: str) -> int:
    u = Unit.query.filter_by(code=code).first()
    if not u:
        raise RuntimeError(f"Unit '{code}' chưa có. Hãy chạy seed_units() trước.")
    return u.id


# -------- Materials --------
def seed_materials():
    materials = [
        # sku, name, category, unit_code, attrs
        (
            "MAT-BOTMI-CAOCAP",
            "Bột mì cao cấp",
            "Nguyên liệu chính",
            "KG",
            {
                "default_supplier": "Công ty Bột mì Bình An",
                "packaging": "Bao 25kg",
                "shelf_life_days": 180,
            },
        ),
        (
            "MAT-DUONG-TINH-LUYEN",
            "Đường tinh luyện",
            "Nguyên liệu chính",
            "KG",
            {
                "default_supplier": "Công ty Đường Biên Hòa",
                "packaging": "Bao 50kg",
                "shelf_life_days": 365,
            },
        ),
        (
            "MAT-TRUNG-GATA",
            "Trứng gà ta",
            "Nguyên liệu chính",
            "PCS",
            {
                "default_supplier": "Trang trại Trứng An Phú",
                "packaging": "Khay 30 quả",
                "shelf_life_days": 14,
            },
        ),
        (
            "MAT-DAU-AN-CAOCAP",
            "Dầu ăn cao cấp",
            "Phụ liệu",
            "KG",
            {
                "default_supplier": "Nhà cung cấp Dầu ABC",
                "packaging": "Can 20kg",
                "shelf_life_days": 365,
            },
        ),
        (
            "MAT-MUT-SEN",
            "Mứt sen",
            "Nhân bánh",
            "KG",
            {
                "default_supplier": "Cơ sở Mứt Sen Hoa Lài",
                "packaging": "Thùng 20kg",
                "shelf_life_days": 150,
            },
        ),
        (
            "PKG-HOP-LOGO-KIDO",
            "Hộp giấy in logo Kido",
            "Bao bì",
            "BOX20KG",
            {
                "default_supplier": "Bao bì Minh Phú",
                "packaging": "Thùng 20kg",
                "qc": "Kiểm tra chất lượng in",
            },
        ),
    ]

    for sku, name, category, unit_code, attrs in materials:
        unit_id = get_unit_id(unit_code)
        m = Material.query.filter_by(sku=sku).first()
        if not m:
            db.session.add(
                Material(
                    sku=sku,
                    name=name,
                    category=category,
                    unit_id=unit_id,
                    attrs=attrs,
                    is_active=True,
                )
            )
        else:
            m.name = name
            m.category = category
            m.unit_id = unit_id
            m.attrs = attrs
            m.is_active = True
    db.session.commit()
    print("✓ Materials seeded/updated")


def seed_suppliers():
    suppliers = [
        Supplier(
            code="SUP001",
            name="Công ty Bột mì Bình An",
            phone="028-3888-1111",
            email="sales@binhanflour.vn",
            address="123 Nguyễn Văn Cừ, Q.5, TP.HCM",
            is_active=True,
        ),
        Supplier(
            code="SUP002",
            name="Công ty Đường Biên Hòa",
            phone="028-3999-2222",
            email="contact@bienhoasugar.vn",
            address="456 Lê Văn Việt, TP.Thủ Đức, TP.HCM",
            is_active=True,
        ),
        Supplier(
            code="SUP003",
            name="Trang trại Trứng An Phú",
            phone="0272-377-3333",
            email="egg@anphufarm.vn",
            address="Xã Tân An, Long An",
            is_active=True,
        ),
        Supplier(
            code="SUP004",
            name="Nhà cung cấp Dầu ABC",
            phone="028-3777-4444",
            email="info@daunuocabc.vn",
            address="789 Quốc lộ 1A, Bình Chánh, TP.HCM",
            is_active=True,
        ),
        Supplier(
            code="SUP005",
            name="Bao bì Minh Phú",
            phone="028-3888-5555",
            email="contact@minhphupackage.vn",
            address="12 Lê Trọng Tấn, Tân Phú, TP.HCM",
            is_active=True,
        ),
    ]

    for s in suppliers:
        exists = Supplier.query.filter_by(code=s.code).first()
        if not exists:
            db.session.add(s)
    db.session.commit()
    print("✓ Suppliers seeded/updated")


if __name__ == "__main__":
    with app.app_context():
        seed_units()
        seed_materials()
        seed_suppliers()
        print("✅ Seeded Unit & Material xong!")
