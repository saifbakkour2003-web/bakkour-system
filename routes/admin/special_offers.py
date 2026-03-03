from datetime import datetime
from flask import Blueprint, render_template, request, redirect, flash, url_for
from flask_babel import gettext as _
from models import db, Product, SpecialOffer
from utils.admin_auth import admin_required


admin_special_offers_bp = Blueprint("admin_special_offers", __name__, url_prefix="/admin/special-offers")

def _parse_dt(v: str):
    v = (v or "").strip()
    if not v:
        return None
    # input type="datetime-local" بيجي هيك: 2026-02-25T18:30
    try:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M")
    except Exception:
        return None

@admin_special_offers_bp.get("/")
@admin_required
def list_offers():
    running = SpecialOffer.query.order_by(SpecialOffer.is_archived.asc(), SpecialOffer.id.desc()).all()
    return render_template("admin/special_offers_list.html", offers=running)

@admin_special_offers_bp.get("/new")
@admin_required
def new_offer():
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/special_offer_form.html", offer=None, products=products)

@admin_special_offers_bp.post("/new")
@admin_required
def create_offer():
    title = (request.form.get("title") or "").strip()
    note = (request.form.get("note") or "").strip() or None
    offer_kind = (request.form.get("offer_kind") or "gift").strip()

    p1 = request.form.get("product1_id")
    p2 = request.form.get("product2_id")
    p3 = request.form.get("third_product_id") or None

    discount_amount = request.form.get("discount_amount") or None
    discount_amount = float(discount_amount) if discount_amount not in (None, "",) else None

    start_at = _parse_dt(request.form.get("start_at"))
    end_at = _parse_dt(request.form.get("end_at"))

    is_active = bool(request.form.get("is_active"))
    is_cancelled = bool(request.form.get("is_cancelled"))

    stock_limit = request.form.get("stock_limit") or None
    stock_limit = int(stock_limit) if stock_limit not in (None, "",) else None

    stock_remaining = request.form.get("stock_remaining") or None
    stock_remaining = int(stock_remaining) if stock_remaining not in (None, "",) else None

    if not title or not (p1 and p2):
        flash(_("يرجى تعبئة العنوان واختيار المنتجين"), "danger")
        return redirect("/admin/special-offers/new")

    # تحقق سريع حسب النوع
    if offer_kind == "bundle_discount" and (discount_amount is None):
        flash(_("خصم الباكج يحتاج قيمة خصم ثابتة"), "danger")
        return redirect("/admin/special-offers/new")

    if offer_kind in ("gift", "third_discount") and not p3:
        flash(_("هذا النوع يحتاج اختيار منتج ثالث"), "danger")
        return redirect("/admin/special-offers/new")

    if offer_kind == "third_discount" and (discount_amount is None):
        flash(_("خصم المنتج الثالث يحتاج قيمة خصم ثابتة"), "danger")
        return redirect("/admin/special-offers/new")

    offer = SpecialOffer(
        title=title,
        note=note,
        offer_kind=offer_kind,
        product1_id=int(p1),
        product2_id=int(p2),
        third_product_id=int(p3) if p3 else None,
        discount_amount=discount_amount,
        start_at=start_at,
        end_at=end_at,
        is_active=is_active,
        is_cancelled=is_cancelled,
        stock_limit=stock_limit,
        stock_remaining=stock_remaining,
    )
    db.session.add(offer)
    db.session.commit()

    flash(_("تم إنشاء العرض ✅"), "success")
    return redirect("/admin/special-offers/")

@admin_special_offers_bp.get("/<int:offer_id>/edit")
@admin_required
def edit_offer(offer_id):
    offer = SpecialOffer.query.get_or_404(offer_id)
    products = Product.query.order_by(Product.id.desc()).all()
    return render_template("admin/special_offer_form.html", offer=offer, products=products)

@admin_special_offers_bp.post("/<int:offer_id>/edit")
@admin_required
def update_offer(offer_id):
    offer = SpecialOffer.query.get_or_404(offer_id)

    offer.title = (request.form.get("title") or "").strip()
    offer.note = (request.form.get("note") or "").strip() or None
    offer.offer_kind = (request.form.get("offer_kind") or "gift").strip()

    offer.product1_id = int(request.form.get("product1_id"))
    offer.product2_id = int(request.form.get("product2_id"))

    p3 = request.form.get("third_product_id") or None
    offer.third_product_id = int(p3) if p3 else None

    v = request.form.get("discount_amount") or None
    offer.discount_amount = float(v) if v not in (None, "",) else None

    offer.start_at = _parse_dt(request.form.get("start_at"))
    offer.end_at = _parse_dt(request.form.get("end_at"))

    offer.is_active = bool(request.form.get("is_active"))
    offer.is_cancelled = bool(request.form.get("is_cancelled"))

    sl = request.form.get("stock_limit") or None
    offer.stock_limit = int(sl) if sl not in (None, "",) else None

    sr = request.form.get("stock_remaining") or None
    offer.stock_remaining = int(sr) if sr not in (None, "",) else None

    db.session.commit()
    flash(_("تم حفظ التعديل ✅"), "success")
    return redirect("/admin/special-offers/")

@admin_special_offers_bp.post("/<int:offer_id>/toggle-cancel")
@admin_required
def toggle_cancel(offer_id):
    offer = SpecialOffer.query.get_or_404(offer_id)
    offer.is_cancelled = not bool(offer.is_cancelled)
    db.session.commit()
    flash(_("تم تحديث حالة العرض"), "info")
    return redirect("/admin/special-offers/")



@admin_special_offers_bp.post("/<int:offer_id>/archive")
@admin_required
def admin_archive_special_offer(offer_id):
    o = SpecialOffer.query.get_or_404(offer_id)
    o.is_archived = True
    if hasattr(o, "archived_at"):
        o.archived_at = datetime.utcnow()
    db.session.commit()
    flash(_("تم إخفاء العرض ✅"), "success")
    return redirect(url_for("admin_special_offers.list_offers"))


@admin_special_offers_bp.post("/<int:offer_id>/unarchive")
@admin_required
def admin_unarchive_special_offer(offer_id):
    o = SpecialOffer.query.get_or_404(offer_id)
    o.is_archived = False
    if hasattr(o, "archived_at"):
        o.archived_at = None
    db.session.commit()
    flash(_("تمت إعادة العرض ✅"), "success")
    return redirect(url_for("admin_special_offers.list_offers"))