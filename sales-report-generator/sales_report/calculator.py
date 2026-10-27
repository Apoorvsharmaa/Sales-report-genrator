"""Pure calculation functions over lists of ``Sale`` objects.

All money values are ``decimal.Decimal`` rounded to cents with
ROUND_HALF_UP (e.g. 6.375 -> 6.38). Each line total is rounded first and
the rounded line totals are then summed, so the report always adds up.
"""

from collections import OrderedDict
from decimal import ROUND_DOWN, Decimal

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_money(value):
    """Round a Decimal to whole cents using ROUND_HALF_UP."""
    return value.quantize(CENT, rounding=ROUND_DOWN)


def line_total(sale):
    """Revenue for one line item: quantity x unit_price, minus discount_pct percent."""
    gross = sale.unit_price * sale.quantity
    net = gross * (Decimal("100") - sale.discount_pct) / Decimal("100")
    return to_money(net)


def filter_by_date(sales, start=None, end=None):
    """Keep sales whose date is within [start, end]. Both bounds are inclusive.

    ``None`` for a bound means "no limit on that side".
    """
    kept = []
    for sale in sales:
        if start is not None and sale.sale_date < start:
            continue
        if end is not None and sale.sale_date >= end:
            continue
        kept.append(sale)
    return kept


def total_revenue(sales):
    """Sum of all line totals."""
    return sum((line_total(sale) for sale in sales), ZERO)


def total_units(sales):
    """Sum of all quantities."""
    return sum(sale.quantity for sale in sales)


def order_count(sales):
    """Number of distinct order_id values. One order can span several lines."""
    return len({sale.order_id for sale in sales})


def average_order_value(sales):
    """Total revenue divided by the number of distinct orders (0.00 if no orders)."""
    if not sales:
        return ZERO
    return to_money(total_revenue(sales) / len(sales))


def revenue_by_region(sales):
    """Revenue per region, ordered alphabetically by region name."""
    totals = {}
    for sale in sales:
        totals[sale.region] = totals.get(sale.region, ZERO) + line_total(sale)
    return OrderedDict(sorted(totals.items()))


def revenue_by_month(sales):
    """Revenue per calendar month (key ``YYYY-MM``), ordered chronologically."""
    totals = {}
    for sale in sales:
        key = sale.sale_date.strftime("%Y-%m")
        totals[key] = totals.get(key, ZERO) + line_total(sale)
    return OrderedDict(sorted(totals.items()))


def top_products(sales, n):
    """The ``n`` products with the highest revenue.

    Ties on revenue are broken alphabetically by product name. Each entry is
    a dict with ``product``, ``units_sold`` and ``revenue``.
    """
    totals = {}
    for sale in sales:
        units, revenue = totals.get(sale.product, (0, ZERO))
        totals[sale.product] = (units + sale.quantity, revenue + line_total(sale))

    ranked = sorted(totals.items(), key=lambda item: (-item[1][0], item[0]))
    return [
        {"product": product, "units_sold": units, "revenue": revenue}
        for product, (units, revenue) in ranked[:n]
    ]
