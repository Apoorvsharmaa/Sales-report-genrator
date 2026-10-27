"""Read sales line items from a CSV file and validate each row.

Valid rows become ``Sale`` objects. Invalid rows are not fatal: they are
recorded as ``SkippedRow`` entries (with the CSV line number and a reason)
so the report can show what was ignored. Problems that make the whole file
unusable (empty file, missing required columns) raise ``SalesDataError``.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

REQUIRED_COLUMNS = ("order_id", "date", "region", "product", "quantity", "unit_price")
OPTIONAL_COLUMNS = ("discount_pct",)
DATE_FORMAT = "%Y-%m-%d"


class SalesDataError(Exception):
    """Raised when the input file as a whole cannot be processed."""


@dataclass(frozen=True)
class Sale:
    """One validated sales line item."""

    order_id: str
    sale_date: date
    region: str
    product: str
    quantity: int
    unit_price: Decimal
    discount_pct: Decimal


@dataclass(frozen=True)
class SkippedRow:
    """A CSV row that failed validation."""

    line: int
    reason: str


def normalize_region(raw):
    """Return a canonical region name: trimmed, single-spaced, Title Case."""
    return " ".join(raw.split())


def _clean(row, column):
    return (row.get(column) or "").strip()


def _parse_decimal(value, field):
    try:
        number = Decimal(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field} is not a number: {value!r}") from None
    if not number.is_finite():
        raise ValueError(f"{field} is not a finite number: {value!r}")
    return number


def _parse_int(value, field):
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{field} is not a whole number: {value!r}") from None


def parse_row(row):
    """Convert one CSV row (a dict) into a ``Sale``.

    Raises ``ValueError`` with a human-readable reason if the row is invalid.
    """
    order_id = _clean(row, "order_id")
    if not order_id:
        raise ValueError("order_id is empty")

    product = _clean(row, "product")
    if not product:
        raise ValueError("product is empty")

    region = normalize_region(_clean(row, "region"))
    if not region:
        raise ValueError("region is empty")

    raw_date = _clean(row, "date")
    try:
        sale_date = datetime.strptime(raw_date, DATE_FORMAT).date()
    except ValueError:
        raise ValueError(f"date is not in YYYY-MM-DD format: {raw_date!r}") from None

    quantity = _parse_int(_clean(row, "quantity"), "quantity")
    if quantity < 0:
        raise ValueError(f"quantity must be greater than zero: {quantity}")

    unit_price = _parse_decimal(_clean(row, "unit_price"), "unit_price")
    if unit_price < 0:
        raise ValueError(f"unit_price cannot be negative: {unit_price}")

    raw_discount = _clean(row, "discount_pct")
    discount_pct = _parse_decimal(raw_discount, "discount_pct") if raw_discount else Decimal("0")
    if not Decimal("0") <= discount_pct <= Decimal("100"):
        raise ValueError(f"discount_pct must be between 0 and 100: {discount_pct}")

    return Sale(
        order_id=order_id,
        sale_date=sale_date,
        region=region,
        product=product,
        quantity=quantity,
        unit_price=unit_price,
        discount_pct=discount_pct,
    )


def load_sales(path):
    """Load a sales CSV file.

    Returns a tuple ``(sales, skipped)`` where ``sales`` is a list of ``Sale``
    and ``skipped`` is a list of ``SkippedRow``.
    """
    sales = []
    skipped = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SalesDataError(f"input file is empty: {path}")

        headers = [name.strip() for name in reader.fieldnames]
        missing = [column for column in REQUIRED_COLUMNS if column not in headers]
        if missing:
            raise SalesDataError(f"missing required column(s): {', '.join(missing)}")
        reader.fieldnames = headers

        for row in reader:
            try:
                sales.append(parse_row(row))
            except ValueError as exc:
                skipped.append(SkippedRow(line=reader.line_num, reason=str(exc)))
    return sales, skipped
