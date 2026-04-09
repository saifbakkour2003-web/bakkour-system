from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


# =======================
# Association Tables
# =======================
sub_category_property = db.Table(
    "sub_category_property",
    db.Column("sub_category_id", db.Integer, db.ForeignKey("sub_category.id"), primary_key=True),
    db.Column("property_id", db.Integer, db.ForeignKey("property.id"), primary_key=True),
)


# =======================
# Customer / Ledgers
# =======================
class Customer(db.Model):
    __tablename__ = "customer"

    id = db.Column(db.Integer, primary_key=True)
    custom_id = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100), nullable=False)
    name_tr = db.Column(db.String(255), nullable=True)

    phone = db.Column(db.String(20), default="")
    notes = db.Column(db.Text, default="")
    ledger = db.Column(db.String(50), default="تقسيط")

    installment_products = db.relationship(
        "InstallmentProduct",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    cash_debts = db.relationship(
        "CashDebt",
        back_populates="customer",
        cascade="all, delete-orphan"
    )

    general_cash_payments = db.relationship(
        "GeneralCashPayment",
        back_populates="customer",
        cascade="all, delete-orphan"
    )


class InstallmentProduct(db.Model):
    __tablename__ = "installment_product"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)

    name = db.Column(db.String(100), nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    initial_payment = db.Column(db.Float, nullable=False, default=0.0)
    monthly_installment = db.Column(db.Float)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    paid_off = db.Column(db.Boolean, default=False)

    customer = db.relationship("Customer", back_populates="installment_products")

    payments = db.relationship(
        "InstallmentPayment",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    items = db.relationship(
        "InstallmentItem",
        back_populates="installment",
        cascade="all, delete-orphan"
    )


class InstallmentItem(db.Model):
    __tablename__ = "installment_item"

    id = db.Column(db.Integer, primary_key=True)

    installment_product_id = db.Column(
        db.Integer,
        db.ForeignKey("installment_product.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    name = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False, default=1)

    product = db.relationship("Product")
    installment = db.relationship("InstallmentProduct", back_populates="items")


class InstallmentPayment(db.Model):
    __tablename__ = "installment_payment"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("installment_product.id"), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(100), default="دفعة تقسيط")

    product = db.relationship("InstallmentProduct", back_populates="payments")


class CashDebt(db.Model):
    __tablename__ = "cash_debt"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)

    # product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    product_id = db.Column(db.Integer, nullable=True)

    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # legacy
    paid_off = db.Column(db.Boolean, default=False)

    customer = db.relationship("Customer", back_populates="cash_debts")


class GeneralCashPayment(db.Model):
    __tablename__ = "general_cash_payment"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("customer.id"), nullable=False)

    amount = db.Column(db.Float, nullable=False)
    date_paid = db.Column(db.DateTime, default=datetime.utcnow)

    # مصدر/سبب الدفعة
    source = db.Column(db.String(100), default="دفعة عامة")

    customer = db.relationship("Customer", back_populates="general_cash_payments")


# =======================
# Users
# =======================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    customer_ref_code = db.Column(db.String(50), nullable=True)

    first_name = db.Column(db.String(120), nullable=True)
    last_name = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # buyer / admin
    role = db.Column(db.String(20), nullable=False, default="buyer")

    # pending / active / blocked
    status = db.Column(db.String(20), nullable=False, default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def can_view_prices(self) -> bool:
        return (self.role == "admin") or (self.status == "active")


# =======================
# Categories / Properties
# =======================
class MainCategory(db.Model):
    __tablename__ = "main_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    name_tr = db.Column(db.String(255), nullable=True)
    code_prefix = db.Column(db.String(10), nullable=False)

    # legacy / fixed departments backing rows
    department = db.Column(db.String(20), nullable=False, default="electrical")

    sub_categories = db.relationship(
        "SubCategory",
        back_populates="main_category",
        cascade="all, delete-orphan"
    )


class SubCategory(db.Model):
    __tablename__ = "sub_category"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_tr = db.Column(db.String(255), nullable=True)

    code_prefix = db.Column(db.String(10), nullable=False)
    department = db.Column(db.String(20), nullable=False, default="electrical")

    # legacy compatibility
    main_category_id = db.Column(db.Integer, db.ForeignKey("main_category.id"), nullable=False)
    main_category = db.relationship("MainCategory", back_populates="sub_categories")

    properties = db.relationship(
        "Property",
        secondary=sub_category_property,
        back_populates="sub_categories"
    )


class Property(db.Model):
    __tablename__ = "property"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    name_tr = db.Column(db.String(255), nullable=True)

    # text / number / select
    input_type = db.Column(db.String(20), nullable=False)

    department = db.Column(db.String(20), nullable=False, default="electrical")
    is_required = db.Column(db.Boolean, default=False)

    # خاصية عامة لكل المنتجات
    is_global = db.Column(db.Boolean, default=False)

    sub_category_id = db.Column(db.Integer, db.ForeignKey("sub_category.id"), nullable=True)

    # legacy relationship
    sub_category = db.relationship("SubCategory", foreign_keys=[sub_category_id])

    # many-to-many sub categories
    sub_categories = db.relationship(
        "SubCategory",
        secondary=sub_category_property,
        back_populates="properties"
    )

    values = db.relationship(
        "PropertyValue",
        back_populates="property",
        cascade="all, delete-orphan"
    )


class PropertyValue(db.Model):
    __tablename__ = "property_value"

    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(100), nullable=False)
    value_tr = db.Column(db.String(100), nullable=True)

    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)

    property = db.relationship("Property", back_populates="values")


class Brand(db.Model):
    __tablename__ = "brand"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(10), nullable=False, unique=True)
    department = db.Column(db.String(20), nullable=False, default="electrical")

    products = db.relationship("Product", back_populates="brand_rel")


# =======================
# Products
# =======================
class Product(db.Model):
    __tablename__ = "product"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)

    # Barcode
    barcode_value = db.Column(db.String(60), nullable=True)
    barcode_image = db.Column(db.String(255), nullable=True)

    # Department
    department = db.Column(db.String(20), nullable=False, default="electrical")

    # Serial
    serial_no = db.Column(db.String(40), unique=True, nullable=True)

    # availability + stock
    is_available = db.Column(db.Boolean, default=True)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)

    name = db.Column(db.String(200), nullable=False)
    name_tr = db.Column(db.String(255), nullable=True)

    description = db.Column(db.Text, nullable=True)
    description_tr = db.Column(db.Text, nullable=True)

    # legacy fields
    brand = db.Column(db.String(100))
    color = db.Column(db.String(50))
    size = db.Column(db.String(50))

    # brand relation
    brand_id = db.Column(db.Integer, db.ForeignKey("brand.id"), nullable=True)
    brand_rel = db.relationship("Brand", back_populates="products")

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    capital_price = db.Column(db.Float, nullable=False)
    base_cash_price = db.Column(db.Float, nullable=False)

    sub_category_id = db.Column(db.Integer, db.ForeignKey("sub_category.id"), nullable=False)
    sub_category = db.relationship("SubCategory")

    # Discount
    is_discounted = db.Column(db.Boolean, default=False)
    discount_price = db.Column(db.Float, nullable=True)
    discount_start = db.Column(db.DateTime, nullable=True)
    discount_end = db.Column(db.DateTime, nullable=True)

    properties = db.relationship(
        "ProductProperty",
        back_populates="product",
        cascade="all, delete-orphan"
    )

    images = db.relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order.asc(), ProductImage.id.asc()",
    )

    variants = db.relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.sort_order.asc(), ProductVariant.id.asc()",
    )

    @property
    def price(self) -> float:
        try:
            return float(self.base_cash_price or 0)
        except Exception:
            return 0.0

    @property
    def is_discount_active(self) -> bool:
        if not bool(self.is_discounted):
            return False

        if self.discount_price is None:
            return False

        try:
            if float(self.discount_price) <= 0:
                return False
        except Exception:
            return False

        now = datetime.utcnow()

        if self.discount_start and now < self.discount_start:
            return False
        if self.discount_end and now > self.discount_end:
            return False

        return True

    @property
    def effective_price(self) -> float:
        try:
            return float(self.discount_price) if self.is_discount_active else float(self.base_cash_price or 0)
        except Exception:
            return float(self.base_cash_price or 0)

    @property
    def has_variants(self):
        return bool(self.variants)


class ProductProperty(db.Model):
    __tablename__ = "product_property"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    property_id = db.Column(db.Integer, db.ForeignKey("property.id"), nullable=False)

    value = db.Column(db.String(100), nullable=False)
    value_tr = db.Column(db.String(255), nullable=True)

    product = db.relationship("Product", back_populates="properties")
    property = db.relationship("Property")


class ProductImage(db.Model):
    __tablename__ = "product_image"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False, index=True)
    image_path = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    product = db.relationship("Product", back_populates="images")


class ProductVariant(db.Model):
    __tablename__ = "product_variant"

    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    size = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(50), nullable=True)

    capital_price = db.Column(db.Float, nullable=False, default=0)
    base_cash_price = db.Column(db.Float, nullable=False, default=0)

    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    is_available = db.Column(db.Boolean, nullable=False, default=True)

    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    product = db.relationship("Product", back_populates="variants")


# =======================
# Sales
# =======================
class Sale(db.Model):
    __tablename__ = "sale"

    id = db.Column(db.Integer, primary_key=True)

    # صار Nullable لبيع يدوي
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=True
    )

    customer_id = db.Column(
        db.Integer,
        db.ForeignKey("customer.id"),
        nullable=True
    )

    sale_type = db.Column(db.String(20), nullable=False)

    sell_price = db.Column(db.Float, nullable=False)
    cost_price = db.Column(db.Float, nullable=False)

    # معلومات إضافية للبيع اليدوي
    manual_name = db.Column(db.String(200), nullable=True)
    manual_code = db.Column(db.String(60), nullable=True)

    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")
    customer = db.relationship("Customer")


# =======================
# Special Offers
# =======================
class SpecialOffer(db.Model):
    __tablename__ = "special_offer"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    note = db.Column(db.String(255), nullable=True)

    # gift | bundle_discount | third_discount
    offer_kind = db.Column(db.String(30), nullable=False, default="gift")

    product1_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    product2_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    third_product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=True)

    # خصم ثابت
    discount_amount = db.Column(db.Float, nullable=True)

    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(db.Boolean, default=True)
    is_cancelled = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ستوك يدوي
    stock_limit = db.Column(db.Integer, nullable=True)
    stock_remaining = db.Column(db.Integer, nullable=True)

    product1 = db.relationship("Product", foreign_keys=[product1_id])
    product2 = db.relationship("Product", foreign_keys=[product2_id])
    third_product = db.relationship("Product", foreign_keys=[third_product_id])

    @property
    def is_time_active(self):
        now = datetime.utcnow()
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True

    @property
    def has_stock(self):
        if self.stock_remaining is None:
            return True
        return self.stock_remaining > 0

    @property
    def is_running(self):
        return bool(self.is_active) and (not self.is_cancelled) and self.is_time_active and self.has_stock


# =======================
# Coupons
# =======================
class Coupon(db.Model):
    __tablename__ = "coupon"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False, index=True)

    title = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # خصم ثابت (مبلغ)
    discount_amount = db.Column(db.Float, nullable=False, default=0)

    usage_limit = db.Column(db.Integer, nullable=True)
    usage_count = db.Column(db.Integer, nullable=False, default=0)

    start_at = db.Column(db.DateTime, nullable=True)
    end_at = db.Column(db.DateTime, nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # لأول X أشخاص يسجلوا دخول
    auto_claim = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def remaining(self):
        if self.usage_limit is None:
            return None
        return max(int(self.usage_limit) - int(self.usage_count or 0), 0)

    def is_running_now(self, now=None):
        now = now or datetime.now()
        if not self.is_active:
            return False
        if self.usage_limit is not None and (self.usage_count or 0) >= self.usage_limit:
            return False
        if self.start_at and now < self.start_at:
            return False
        if self.end_at and now > self.end_at:
            return False
        return True


class UserCoupon(db.Model):
    __tablename__ = "user_coupon"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    coupon_id = db.Column(db.Integer, db.ForeignKey("coupon.id"), nullable=False, index=True)

    claimed_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("coupons", lazy="dynamic"))
    coupon = db.relationship("Coupon")

    __table_args__ = (
        db.UniqueConstraint("user_id", "coupon_id", name="uq_user_coupon"),
    )