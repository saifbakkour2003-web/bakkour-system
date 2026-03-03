# utils/stock_utils.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class StockResult:
    ok: bool
    changed: bool = False
    before: int | None = None
    after: int | None = None
    error: str | None = None

def try_deduct_stock(product, qty: int, *, block_if_insufficient: bool = False) -> StockResult:
    try:
        qty = int(qty)
    except Exception:
        return StockResult(ok=False, error="bad_qty")

    if qty <= 0:
        return StockResult(ok=True, changed=False)

    before = int(product.stock_qty or 0)
    after = before - qty

    # ✅ سلوكك المطلوب: صفّر فقط
    if after < 0:
        after = 0

    if after != before:
        product.stock_qty = after
        if after == 0:
            product.is_available = False
        return StockResult(ok=True, changed=True, before=before, after=after)

    return StockResult(ok=True, changed=False, before=before, after=after)
