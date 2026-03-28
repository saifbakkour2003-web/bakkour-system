# routes/admin/products.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, abort
from flask_babel import gettext as _, get_locale
from datetime import datetime
from sqlalchemy.orm import joinedload
import os

from extensions import db
from models import (
    Product, SubCategory, ProductProperty, Property, Brand, MainCategory,
    PropertyValue, ProductImage, ProductVariant
)
from utils.product_fetch import get_products_query
from utils.product_code import generate_product_code
from utils.barcode_utils import generate_barcode
from utils.upload import save_product_image
from utils.admin_auth import admin_required


DEPT_LABELS = {
    "electrical": "كهربائيات",
    "linens": "بياضات",
    "crystal": "بلوريات"
}

ALLOWED_DEPTS = {"electrical", "linens", "crystal"}

products_bp = Blueprint("products", __name__, url_prefix="/products")


def norm_val(v: str | None) -> str:
    return " ".join((v or "").strip().split()).lower()


def build_props_signature(all_props, form):
    pairs = []
    for prop in all_props:
        v = norm_val(form.get(f"property_{prop.id}"))
        if v:
            pairs.append((prop.id, v))
    pairs.sort(key=lambda x: x[0])
    return tuple(pairs)


def existing_props_signature(product: Product):
    pairs = []
    for pp in product.properties:
        v = norm_val(pp.value)
        if v:
            pairs.append((pp.property_id, v))
    pairs.sort(key=lambda x: x[0])
    return tuple(pairs)


def normalize_dept(dept: str | None) -> str | None:
    d = (dept or "").strip().lower()
    return d if d in ALLOWED_DEPTS else None


def get_subcategories_by_dept(dept: str):
    return (
        SubCategory.query
        .join(MainCategory)
        .filter(MainCategory.department == dept)
        .order_by(SubCategory.name.asc())
        .all()
    )


def get_brands_by_dept(dept: str):
    return (
        Brand.query
        .filter(Brand.department == dept)
        .order_by(Brand.name.asc())
        .all()
    )


def get_allowed_properties_for_subcategory(sub: SubCategory, dept: str):
    global_props = Property.query.filter(
        Property.department == dept,
        Property.is_global == True
    ).all()

    scoped_props = list(sub.properties or [])
    return list({p.id: p for p in (global_props + scoped_props)}.values())

def parse_variants_from_form(form):
    sizes = form.getlist("variant_size[]")
    colors = form.getlist("variant_color[]")
    capitals = form.getlist("variant_capital_price[]")
    prices = form.getlist("variant_base_cash_price[]")
    stocks = form.getlist("variant_stock_qty[]")

    variants = []
    max_len = max(
        len(sizes),
        len(colors),
        len(capitals),
        len(prices),
        len(stocks),
        0
    )

    for i in range(max_len):
        size = (sizes[i] if i < len(sizes) else "").strip()
        color = (colors[i] if i < len(colors) else "").strip() or None
        capital_raw = (capitals[i] if i < len(capitals) else "").strip()
        price_raw = (prices[i] if i < len(prices) else "").strip()
        stock_raw = (stocks[i] if i < len(stocks) else "").strip()

        # إذا الصف فاضي كله، نتجاهله
        if not size and not color and not capital_raw and not price_raw and not stock_raw:
            continue

        if not size or not capital_raw or not price_raw:
            raise ValueError("كل صف مقاس يحتاج: مقاس + رأس مال + سعر بيع")

        try:
            capital_price = float(capital_raw)
            base_cash_price = float(price_raw)
            stock_qty = int(stock_raw) if stock_raw else 0
        except Exception:
            raise ValueError("قيم المقاسات غير صالحة")

        variants.append({
            "size": size,
            "color": color,
            "capital_price": capital_price,
            "base_cash_price": base_cash_price,
            "stock_qty": max(0, stock_qty),
            "is_available": max(0, stock_qty) > 0,
            "sort_order": i,
        })

    return variants


def replace_product_variants(product, variants_data):
    ProductVariant.query.filter_by(product_id=product.id).delete()

    for item in variants_data:
        db.session.add(ProductVariant(
            product_id=product.id,
            size=item["size"],
            color=item["color"],
            capital_price=item["capital_price"],
            base_cash_price=item["base_cash_price"],
            stock_qty=item["stock_qty"],
            is_available=item["is_available"],
            sort_order=item["sort_order"],
        ))


# =========================
# عرض المنتجات
# =========================
@products_bp.route("/")
@admin_required
def products_list():
    dept = (request.args.get("dept") or "").strip().lower()
    if dept not in ("electrical", "linens", "crystal"):
        dept = None

    sub_id_raw = (request.args.get("sub") or "").strip()
    try:
        sub_id = int(sub_id_raw) if sub_id_raw else None
    except Exception:
        sub_id = None

    q = get_products_query(dept=dept, for_shop=False, include_inactive=True)

    if sub_id:
        sub_obj = SubCategory.query.get(sub_id)
        if not sub_obj:
            sub_id = None
        else:
            if dept and (sub_obj.department != dept):
                flash(_("⚠️ التصنيف المختار لا ينتمي لهذا القسم."), "warning")
                return redirect(url_for("products.products_list", dept=dept))
            q = q.filter(Product.sub_category_id == sub_id)

    products = q.all()

    sub_categories = []
    if dept:
        sub_categories = (
            SubCategory.query
            .join(MainCategory)
            .filter(MainCategory.department == dept)
            .order_by(SubCategory.name.asc())
            .all()
        )

    props_text_ar = {}
    props_text_tr = {}

    for prod in products:
        values_ar = []
        values_tr = []

        for pp in sorted(prod.properties, key=lambda x: x.property_id):
            ar = (getattr(pp, "value", None) or "").strip()
            tr = (getattr(pp, "value_tr", None) or "").strip() or ar

            if ar:
                values_ar.append(ar)
            if tr:
                values_tr.append(tr)

        props_text_ar[prod.id] = " | ".join(values_ar)
        props_text_tr[prod.id] = " | ".join(values_tr)

    return render_template(
        "products/list.html",
        products=products,
        props_text_ar=props_text_ar,
        props_text_tr=props_text_tr,
        dept=dept,
        dept_label=DEPT_LABELS.get(dept, _("كل المنتجات")),
        sub_categories=sub_categories,
        selected_sub_id=sub_id
    )


@products_bp.route("/electrical")
@admin_required
def products_electrical():
    return redirect(url_for("products.products_list", dept="electrical"))


@products_bp.route("/linens")
@admin_required
def products_linens():
    return redirect(url_for("products.products_list", dept="linens"))


@products_bp.route("/crystal")
@admin_required
def products_crystal():
    return redirect(url_for("products.products_list", dept="crystal"))


@products_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_product():
    flash(_("⚠️ إضافة المنتج لازم تكون من صفحة القسم (كهربائيات/بياضات/بلوريات)."), "warning")
    return redirect(url_for("products.products_electrical"))


@products_bp.route("/<department>/add", methods=["GET", "POST"])
@admin_required
def add_product_by_department(department):
    department = normalize_dept(department)
    if not department:
        flash(_("قسم غير صالح"), "danger")
        return redirect(url_for("products.products_list"))

    sub_categories = get_subcategories_by_dept(department)
    brands = get_brands_by_dept(department)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        name_tr = (request.form.get("name_tr") or "").strip() or None
        sub_category_id = request.form.get("sub_category_id")
        brand_id = request.form.get("brand_id")
        capital_price = request.form.get("capital_price")
        base_cash_price = request.form.get("base_cash_price")

        if not name or not sub_category_id or not brand_id or not capital_price or not base_cash_price:
            flash(_("كل الحقول الأساسية مطلوبة"), "danger")
            return redirect(request.url)

        sub = SubCategory.query.get_or_404(int(sub_category_id))
        brand = Brand.query.get_or_404(int(brand_id))

        if normalize_dept(sub.department) != department:
            flash(_("⚠️ لا يمكن اختيار تصنيف من قسم مختلف."), "danger")
            return redirect(request.url)

        if normalize_dept(brand.department) != department:
            flash(_("⚠️ لا يمكن اختيار ماركة من قسم مختلف."), "danger")
            return redirect(request.url)

        all_props = get_allowed_properties_for_subcategory(sub, department)

        name_norm = norm_val(name)
        new_sig = build_props_signature(all_props, request.form)

        candidates = (
            Product.query
            .options(joinedload(Product.properties))
            .filter(
                Product.department == department,
                Product.sub_category_id == sub.id,
                Product.brand_id == brand.id
            ).all()
        )

        for ex in candidates:
            if norm_val(ex.name) != name_norm:
                continue
            if existing_props_signature(ex) == new_sig:
                flash(_("⚠️ هذا المنتج موجود مسبقًا بنفس الخصائص (كود: %(code)s)", code=ex.code), "warning")
                return redirect(url_for("products.products_list", dept=department))

        code = generate_product_code(
            sub.main_category.code_prefix,
            sub.code_prefix,
            brand.code
        )

        product = Product(
            code=code,
            barcode_value=code,
            name=name,
            name_tr=name_tr,
            department=department,
            capital_price=float(capital_price),
            base_cash_price=float(base_cash_price),
            sub_category_id=sub.id,
            brand_id=brand.id
        )

        product.description = request.form.get("description") or None
        product.description_tr = request.form.get("description_tr") or None

        variants_data = []
        if department == "linens":
            try:
                variants_data = parse_variants_from_form(request.form)
            except ValueError as e:
                db.session.rollback()
                flash(str(e), "danger")
                return redirect(request.url)

        db.session.add(product)
        db.session.flush()

        if not product.serial_no:
            prefix_map = {"electrical": "E", "linens": "L", "crystal": "C"}
            prefix = prefix_map.get(product.department, "X")
            product.serial_no = f"{prefix}-{product.id:06d}"

        if not product.barcode_value:
            product.barcode_value = product.code

        product.barcode_image = generate_barcode(product.barcode_value, product.id)

        for p in all_props:
            field_name = f"property_{p.id}"
            value = (request.form.get(field_name) or "").strip()

            if p.is_required and not value:
                db.session.rollback()
                flash(_("الخاصية '%(name)s' إلزامية", name=p.name), "danger")
                return redirect(request.url)

            if value:
                pp = ProductProperty(
                    product_id=product.id,
                    property_id=p.id,
                    value=value
                )

                if p.input_type == "select":
                    val_obj = PropertyValue.query.filter_by(property_id=p.id, value=value).first()
                    pp.value_tr = (val_obj.value_tr if val_obj else None)

                db.session.add(pp)

        files = request.files.getlist("images")
        for f in files:
            if not f or not f.filename:
                continue

            rel_path = save_product_image(
                f,
                upload_folder=current_app.config["UPLOAD_FOLDER_PRODUCTS"],
                allowed_exts=current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )

            img = ProductImage(
                product_id=product.id,
                image_path=rel_path,
                sort_order=0
            )
            db.session.add(img)

        if department == "linens" and variants_data:
            replace_product_variants(product, variants_data)
        
        db.session.commit()
        flash(_("تمت إضافة المنتج بنجاح ✅"), "success")
        return redirect(url_for("products.products_list", dept=department))

    return render_template(
        "products/add.html",
        sub_categories=sub_categories,
        brands=brands,
        forced_department=department,
        forced_department_label=DEPT_LABELS.get(department, department)
    )


@products_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    product_dept = normalize_dept(product.department) or "electrical"

    sub_categories = get_subcategories_by_dept(product_dept)
    brands = get_brands_by_dept(product_dept)

    existing_map = {pp.property_id: pp.value for pp in product.properties}

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        product.name_tr = (request.form.get("name_tr") or "").strip() or None
        sub_category_id = request.form.get("sub_category_id")
        brand_id = request.form.get("brand_id")
        capital_price = request.form.get("capital_price")
        base_cash_price = request.form.get("base_cash_price")

        # ✅ (كان مكرر عندك) خليناه مرة وحدة
        product.description = request.form.get("description") or None
        product.description_tr = request.form.get("description_tr") or None

        variants_data = []
        if product_dept == "linens":
            try:
                variants_data = parse_variants_from_form(request.form)
            except ValueError as e:
                flash(str(e), "danger")
                return redirect(request.url)

        product.is_discounted = (request.form.get("is_discounted") == "on")
        discount_price = request.form.get("discount_price")
        product.discount_price = float(discount_price) if discount_price else None

        start = request.form.get("discount_start")
        end = request.form.get("discount_end")
        product.discount_start = datetime.fromisoformat(start) if start else None
        product.discount_end = datetime.fromisoformat(end) if end else None

        if not name or not sub_category_id or not brand_id or not capital_price or not base_cash_price:
            flash(_("كل الحقول الأساسية مطلوبة"), "danger")
            return redirect(request.url)

        sub = SubCategory.query.get_or_404(int(sub_category_id))
        brand = Brand.query.get_or_404(int(brand_id))

        if normalize_dept(sub.department) != product_dept:
            flash(_("⚠️ لا يمكن اختيار تصنيف من قسم مختلف."), "danger")
            return redirect(request.url)

        if normalize_dept(brand.department) != product_dept:
            flash(_("⚠️ لا يمكن اختيار ماركة من قسم مختلف."), "danger")
            return redirect(request.url)

        all_props = get_allowed_properties_for_subcategory(sub, product_dept)

        name_norm = norm_val(name)
        new_sig = build_props_signature(all_props, request.form)

        candidates = (
            Product.query
            .options(joinedload(Product.properties))
            .filter(
                Product.id != product.id,
                Product.department == product_dept,
                Product.sub_category_id == sub.id,
                Product.brand_id == brand.id
            ).all()
        )

        for ex in candidates:
            if norm_val(ex.name) != name_norm:
                continue
            if existing_props_signature(ex) == new_sig:
                flash(_("⚠️ يوجد منتج مطابق بنفس الخصائص (كود: %(code)s)", code=ex.code), "warning")
                return redirect(request.url)

        product.name = name
        product.sub_category_id = sub.id
        product.brand_id = brand.id
        product.capital_price = float(capital_price)
        product.base_cash_price = float(base_cash_price)

        ProductProperty.query.filter_by(product_id=product.id).delete()

        for p in all_props:
            field_name = f"property_{p.id}"
            value = (request.form.get(field_name) or "").strip()

            if p.is_required and not value:
                db.session.rollback()
                flash(_("الخاصية '%(name)s' إلزامية", name=p.name), "danger")
                return redirect(request.url)

            if value:
                pp = ProductProperty(
                    product_id=product.id,
                    property_id=p.id,
                    value=value
                )

                if p.input_type == "select":
                    val_obj = PropertyValue.query.filter_by(property_id=p.id, value=value).first()
                    pp.value_tr = (val_obj.value_tr if val_obj else None)

                db.session.add(pp)

        files = request.files.getlist("images")
        for f in files:
            if not f or not f.filename:
                continue

            rel_path = save_product_image(
                f,
                upload_folder=current_app.config["UPLOAD_FOLDER_PRODUCTS"],
                allowed_exts=current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
            )

            img = ProductImage(
                product_id=product.id,
                image_path=rel_path,
                sort_order=0
            )
            db.session.add(img)

        if product_dept == "linens":
            replace_product_variants(product, variants_data)

        db.session.commit()
        flash(_("تم تعديل المنتج بنجاح ✅"), "success")
        return redirect(url_for("products.products_list", dept=product_dept))

    current_sub = SubCategory.query.get(product.sub_category_id)

    if current_sub and normalize_dept(current_sub.department) == product_dept:
        initial_props = get_allowed_properties_for_subcategory(current_sub, product_dept)
    else:
        initial_props = Property.query.filter(
            Property.department == product_dept,
            Property.is_global == True
        ).order_by(Property.id.asc()).all()

    return render_template(
        "products/edit.html",
        product=product,
        sub_categories=sub_categories,
        brands=brands,
        existing_map=existing_map,
        initial_props=list(initial_props),
        variants= list(product.variants)
    )


@products_bp.route("/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    ProductProperty.query.filter_by(product_id=product.id).delete()
    db.session.delete(product)
    db.session.commit()

    flash(_("تم حذف المنتج 🗑️"), "success")
    return redirect(url_for("products.products_list", dept=normalize_dept(product.department)))


@products_bp.route("/api/properties/<int:sub_category_id>")
@admin_required
def api_properties(sub_category_id):
    sub = SubCategory.query.get_or_404(sub_category_id)
    dept = normalize_dept(sub.department) or "electrical"

    props = (
        Property.query
        .filter(Property.department == dept)
        .filter(
            (Property.is_global == True) |
            (Property.sub_categories.any(SubCategory.id == sub_category_id))
        )
        .order_by(Property.id.asc())
        .all()
    )

    lang = str(get_locale() or "ar").lower()
    is_tr = lang.startswith("tr")

    result = []
    for p in props:
        item = {
            "id": p.id,
            "name": (p.name_tr or p.name) if is_tr else p.name,
            "input_type": p.input_type,
            "is_required": bool(p.is_required),
            "values": []
        }

        if p.input_type == "select":
            item["values"] = [
                {"value": v.value, "label": (v.value_tr or v.value) if is_tr else v.value}
                for v in p.values
            ]

        result.append(item)

    return jsonify(result)


@products_bp.route("/api/properties")
@admin_required
def api_properties_by_dept():
    dept = normalize_dept(request.args.get("dept")) or "electrical"

    props = (
        Property.query
        .filter(Property.department == dept)
        .order_by(Property.id.asc())
        .all()
    )

    lang = str(get_locale() or "ar").lower()
    is_tr = lang.startswith("tr")

    result = []
    for p in props:
        item = {
            "id": p.id,
            "name": (p.name_tr or p.name) if is_tr else p.name,
            "input_type": p.input_type,
            "is_required": bool(p.is_required),
            "values": []
        }

        if p.input_type == "select":
            item["values"] = [
                {"value": v.value, "label": (v.value_tr or v.value) if is_tr else v.value}
                for v in p.values
            ]

        result.append(item)

    return jsonify(result)


# =========================
# Stock Controls
# =========================
@products_bp.route("/<int:product_id>/stock/inc", methods=["POST"])
@admin_required
def stock_inc(product_id):
    product = Product.query.get_or_404(product_id)
    product.stock_qty = int(product.stock_qty or 0) + 1
    if product.stock_qty > 0:
        product.is_available = True
    db.session.commit()
    flash(_("✅ تم زيادة الكمية"), "success")
    return redirect(request.referrer or url_for("products.products_list", dept=normalize_dept(product.department)))


@products_bp.route("/<int:product_id>/stock/dec", methods=["POST"])
@admin_required
def stock_dec(product_id):
    product = Product.query.get_or_404(product_id)
    product.stock_qty = max(0, int(product.stock_qty or 0) - 1)
    if product.stock_qty == 0:
        product.is_available = False
    db.session.commit()
    flash(_("✅ تم إنقاص الكمية"), "success")
    return redirect(request.referrer or url_for("products.products_list", dept=normalize_dept(product.department)))


@products_bp.route("/<int:product_id>/stock/set", methods=["POST"])
@admin_required
def stock_set(product_id):
    product = Product.query.get_or_404(product_id)
    qty = (request.form.get("qty") or "").strip()

    try:
        qty = int(qty)
    except Exception:
        qty = int(product.stock_qty or 0)

    product.stock_qty = max(0, qty)
    product.is_available = (product.stock_qty > 0)
    db.session.commit()

    flash(_("✅ تم تحديث الكمية"), "success")
    return redirect(request.referrer or url_for("products.products_list", dept=normalize_dept(product.department)))


@products_bp.route("/<int:product_id>/toggle-available", methods=["POST"])
@admin_required
def toggle_available(product_id):
    product = Product.query.get_or_404(product_id)
    product.is_available = not bool(product.is_available)
    db.session.commit()
    flash(_("✅ تم تحديث حالة التوفر"), "success")
    return redirect(request.referrer or url_for("products.products_list", dept=normalize_dept(product.department)))


@products_bp.post("/<int:product_id>/images/<int:image_id>/delete")
@admin_required
def delete_product_image(product_id, image_id):
    img = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
    if not img:
        abort(404)

    try:
        abs_path = os.path.join(current_app.root_path, "static", img.image_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except Exception:
        pass

    db.session.delete(img)
    db.session.commit()

    flash(_("تم حذف الصورة."), "success")
    return redirect(url_for("products.edit_product", product_id=product_id))


@products_bp.post("/<int:product_id>/images/<int:image_id>/make-primary")
@admin_required
def make_primary_product_image(product_id, image_id):
    product = Product.query.get_or_404(product_id)

    imgs = list(product.images)
    target = next((im for im in imgs if im.id == image_id), None)
    if not target:
        abort(404)

    # ✅ reset ثم ترتيب جديد (مضمون ما يصير 2 صفر)
    for im in imgs:
        im.sort_order = 9999

    target.sort_order = 0

    i = 1
    for im in sorted(imgs, key=lambda x: x.id):
        if im.id == target.id:
            continue
        im.sort_order = i
        i += 1

    db.session.commit()
    flash(_("تم تعيين الصورة الأساسية ✅"), "success")
    return redirect(url_for("products.edit_product", product_id=product_id))