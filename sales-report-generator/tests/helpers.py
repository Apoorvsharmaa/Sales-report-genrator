"""Shared helpers for the test suite."""

import os
import tempfile
from datetime import date
from decimal import Decimal

from sales_report.loader import Sale

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
EXPECTED_DIR = os.path.join(REPO_ROOT, "expected_output")

HEADER = "order_id,date,region,product,quantity,unit_price,discount_pct"


def make_sale(order_id="1", day=date(2026, 1, 1), region="North", product="Widget",
              quantity=1, unit_price="10.00", discount_pct="0"):
    """Build a Sale with sensible defaults so tests only state what matters."""
    return Sale(
        order_id=order_id,
        sale_date=day,
        region=region,
        product=product,
        quantity=quantity,
        unit_price=Decimal(unit_price),
        discount_pct=Decimal(discount_pct),
    )


class TempCsvMixin:
    """unittest mixin that writes CSV text to a temporary file."""

    def write_csv(self, *rows, header=HEADER):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        with handle:
            handle.write("\n".join([header, *rows]) + "\n")
        self.addCleanup(os.remove, handle.name)
        return handle.name
