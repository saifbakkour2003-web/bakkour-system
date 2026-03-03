# utils/product_fetch.py
"""Shared product fetching/query helpers.

We want ONE consistent query used by both:
  - Admin product pages
  - Shop (customer) product pages

So we avoid duplicated joins and mismatched data between interfaces.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import joinedload

from models import Product, SubCategory, MainCategory, ProductProperty, ProductImage

ALLOWED_DEPTS = {"electrical", "linens", "crystal"}


def normalize_dept(dept: Optional[str]) -> Optional[str]:
    d = (dept or "").strip().lower()
    return d if d in ALLOWED_DEPTS else None


def products_base_query():
    """Base query with all eager-loads used across the app."""
    return (
        Product.query.options(
            joinedload(Product.brand_rel),
            joinedload(Product.sub_category).joinedload(SubCategory.main_category),
            joinedload(Product.properties).joinedload(ProductProperty.property),
        )
    )


def get_products_query(
    *,
    dept: Optional[str] = None,
    sub_category_id: Optional[int] = None,
    for_shop: bool = False,
    include_inactive: bool = False,
):
    """Return a query for listing products."""
    q = products_base_query().order_by(Product.id.desc())

    dept_norm = normalize_dept(dept)
    if dept_norm:
        q = q.filter(Product.department == dept_norm)

    if sub_category_id:
        q = q.filter(Product.sub_category_id == sub_category_id)

    if for_shop:
        q = q.filter(Product.is_active == True)

    # admin: if you ever want to hide inactive by default, you can use include_inactive
    # currently we don't enforce anything here.
    return q


def get_product_by_id(product_id: int, *, for_shop: bool = False):
    """Fetch a single product with all relations eagerly loaded."""
    q = products_base_query().filter(Product.id == product_id)
    if for_shop:
        q = q.filter(Product.is_active == True)
    return q.first()



def products_base_query():
    return (
        Product.query.options(
            joinedload(Product.images),  # ✅ هذا الجديد
            joinedload(Product.brand_rel),
            joinedload(Product.sub_category).joinedload(SubCategory.main_category),
            joinedload(Product.properties).joinedload(ProductProperty.property),
        )
    )
