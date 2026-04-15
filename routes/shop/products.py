from urllib.parse import quote

from flask import render_template, abort, request, current_app
from models import Product, SubCategory
from i18n import pick_lang
from utils.product_fetch import get_products_query, get_product_by_id, normalize_dept

DEPT_LABELS_AR = {
    "electrical": "كهربائيات",
    "linens": "بياضات",
    "crystal": "بلوريات",
}

DEPT_LABELS_TR = {
    "electrical": "Elektrik",
    "linens": "Tekstil",
    "crystal": "Kristal",
}


def _build_props_text(products):
    props_text_ar = {}
    props_text_tr = {}

    for prod in products:
        values_ar, values_tr = [], []

        for pp in sorted(prod.properties, key=lambda x: x.property_id):
            ar = (getattr(pp, "value", "") or "").strip()
            tr = (getattr(pp, "value_tr", "") or "").strip() or ar

            if ar:
                values_ar.append(ar)
            if tr:
                values_tr.append(tr)

        props_text_ar[prod.id] = " | ".join(values_ar)
        props_text_tr[prod.id] = " | ".join(values_tr)

    return props_text_ar, props_text_tr


def _build_specs(product):
    specs = []

    if getattr(product, "department", None):
        specs.append(
            {
                "label": pick_lang("القسم", "Bölüm"),
                "value": pick_lang(
                    DEPT_LABELS_AR.get(product.department, product.department),
                    DEPT_LABELS_TR.get(product.department, product.department),
                ),
            }
        )

    if getattr(product, "sub_category", None) and product.sub_category:
        sc = product.sub_category
        dept_label_ar = DEPT_LABELS_AR.get(sc.department, sc.department)
        dept_label_tr = DEPT_LABELS_TR.get(sc.department, sc.department)

        specs.append(
            {
                "label": pick_lang("التصنيف", "Kategori"),
                "value": pick_lang(
                    f"{dept_label_ar} › {sc.name}",
                    f"{dept_label_tr} › {(sc.name_tr or sc.name)}",
                ),
            }
        )

    if getattr(product, "brand_rel", None):
        specs.append(
            {
                "label": pick_lang("الماركة", "Marka"),
                "value": product.brand_rel.name,
            }
        )

    props_sorted = sorted(
        product.properties,
        key=lambda pp: (pp.property.name if pp.property else "", pp.property_id),
    )

    for pp in props_sorted:
        if not pp.property:
            continue

        label = pick_lang(pp.property.name, pp.property.name_tr or pp.property.name)
        value = pick_lang(pp.value, (pp.value_tr or pp.value))

        if value:
            specs.append({"label": label, "value": value})

    return specs


def _build_whatsapp_link(product, specs):
    wa_number = current_app.config.get("WHATSAPP_PHONE_E164", "")
    if not wa_number:
        return ""

    basic_specs = []
    for s in specs:
        if s.get("label") and s.get("value"):
            basic_specs.append(f"- {s['label']}: {s['value']}")
        if len(basic_specs) >= 6:
            break

    msg_lines = [
        "مرحبًا 👋",
        "أريد الاستفسار عن هذا المنتج:",
        f"الكود: {product.code}",
        f"الاسم: {pick_lang(product.name, product.name_tr)}",
    ]

    if basic_specs:
        msg_lines.append("المواصفات:")
        msg_lines.extend(basic_specs)

    msg = "\n".join(msg_lines)
    return f"https://wa.me/{wa_number}?text={quote(msg)}"


def register(app):
    @app.get("/shop/products")
    def shop_products_list():
        dept_raw = (request.args.get("dept") or "").strip().lower() or None
        dept = normalize_dept(dept_raw)

        sub_raw = (request.args.get("sub") or "").strip()
        sub_id = int(sub_raw) if sub_raw.isdigit() else None

        q = (request.args.get("q") or "").strip()
        only_discounted = (request.args.get("only_discounted") or "").strip() in ("1", "true", "yes", "on")
        sort = (request.args.get("sort") or "").strip()

        query = get_products_query(dept=dept, for_shop=True)

        if sub_id:
            query = query.filter(Product.sub_category_id == sub_id)

        if q:
            like = f"%{q}%"
            query = query.filter(
                Product.name.ilike(like) |
                Product.name_tr.ilike(like) |
                Product.code.ilike(like)
            )

        if only_discounted:
            query = query.filter(
                Product.is_discounted == True,
                Product.discount_price.isnot(None),
            )

        if sort == "price_asc":
            query = query.order_by(Product.price.asc(), Product.id.desc())
        elif sort == "price_desc":
            query = query.order_by(Product.price.desc(), Product.id.desc())
        elif sort == "new":
            query = query.order_by(Product.id.desc())
        else:
            query = query.order_by(Product.id.desc())

        products = query.all()
        props_text_ar, props_text_tr = _build_props_text(products)

        sub_categories_q = SubCategory.query
        if dept:
            sub_categories_q = sub_categories_q.filter(SubCategory.department == dept)

        sub_categories = sub_categories_q.order_by(SubCategory.name.asc()).all()

        return render_template(
            "shop/products.html",
            products=products,
            props_text_ar=props_text_ar,
            props_text_tr=props_text_tr,
            dept=dept,
            dept_labels={"ar": DEPT_LABELS_AR, "tr": DEPT_LABELS_TR},
            pick_lang=pick_lang,
            q=q,
            only_discounted=only_discounted,
            sort=sort,
            sub_id=sub_id,
            sub_categories=sub_categories,
        )

    @app.get("/shop/product/<int:product_id>")
    def shop_product_detail(product_id: int):
        product = get_product_by_id(product_id, for_shop=True)
        if not product:
            abort(404)

        variants = []
        if getattr(product, "group_code", None):
            variants = (
                get_products_query(for_shop=True)
                .filter_by(group_code=product.group_code)
                .order_by(Product.id.asc())
                .all()
            )

        specs = _build_specs(product)
        whatsapp_product_link = _build_whatsapp_link(product, specs)

        if product.variants and len(product.variants) > 0:
            min_price = min(v.base_cash_price for v in product.variants)
        else:
            min_price = product.base_cash_price

        return render_template(
            "shop/product_detail.html",
            product=product,
            variants=variants,
            specs=specs,
            pick_lang=pick_lang,
            whatsapp_product_link=whatsapp_product_link,
            min_price=min_price,
        )