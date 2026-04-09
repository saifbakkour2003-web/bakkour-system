"""Shared product fetching/query helpers.

We keep one consistent query layer used by both:
- Admin product pages
- Shop (customer) product pages

Current architectural direction:
- Department is fixed: electrical / linens / crystal
- Product belongs to SubCategory
- SubCategory is the practical source of department grouping
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import joinedload

from models import Product, SubCategory, ProductProperty


ALLOWED_DEPTS = {"electrical", "linens", "crystal"}


# =========================
# Department helpers
# =========================
def normalize_dept(dept: Optional[str]) -> Optional[str]:
    d = (dept or "").strip().lower()
    return d if d in ALLOWED_DEPTS else None


# =========================
# Base query
# =========================
def products_base_query():
    """Base query with eager-loads used across admin + shop."""
    return (
        Product.query.options(
            joinedload(Product.images),
            joinedload(Product.variants),
            joinedload(Product.brand_rel),
            joinedload(Product.sub_category).joinedload(SubCategory.main_category),
            joinedload(Product.properties).joinedload(ProductProperty.property),
        )
    )


# =========================
# Listing query
# =========================
def get_products_query(
    *,
    dept: Optional[str] = None,
    sub_category_id: Optional[int] = None,
    for_shop: bool = False,
    include_inactive: bool = False,
):
    """Return a query for product listing."""

    q = products_base_query()

    dept_norm = normalize_dept(dept)
    if dept_norm:
        q = q.filter(Product.department == dept_norm)

    if sub_category_id:
        q = q.filter(Product.sub_category_id == sub_category_id)

    if for_shop:
        q = q.filter(Product.is_active == True)

    # currently we keep admin products visible by default
    # include_inactive is kept for API compatibility / future use
    return q


# =========================
# Single product query
# =========================
def get_product_by_id(product_id: int, *, for_shop: bool = False):
    """Fetch one product with all needed relations eagerly loaded."""
    q = products_base_query().filter(Product.id == product_id)

    if for_shop:
        q = q.filter(Product.is_active == True)

    return q.first()