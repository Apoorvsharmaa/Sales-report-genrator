"""Tests for the pure calculation functions."""

import unittest
from datetime import date
from decimal import Decimal

from sales_report import calculator
from tests.helpers import make_sale


class LineTotalTest(unittest.TestCase):
    def test_line_total_without_discount(self):
        self.assertEqual(calculator.line_total(make_sale(quantity=2, unit_price="89.00")), Decimal("178.00"))

    def test_line_total_applies_percentage_discount(self):
        sale = make_sale(quantity=1, unit_price="49.99", discount_pct="10")
        self.assertEqual(calculator.line_total(sale), Decimal("44.99"))

    def test_line_total_rounds_half_cent_up(self):
        # 3 x 2.50 = 7.50, minus 15% = 6.375 -> 6.38 (ROUND_HALF_UP)
        sale = make_sale(quantity=3, unit_price="2.50", discount_pct="15")
        self.assertEqual(calculator.line_total(sale), Decimal("6.38"))

    def test_line_total_rounds_below_half_cent_down(self):
        # 1 x 39.99, minus 12.5% = 34.99125 -> 34.99
        sale = make_sale(quantity=1, unit_price="39.99", discount_pct="12.5")
        self.assertEqual(calculator.line_total(sale), Decimal("34.99"))

    def test_full_discount_gives_zero(self):
        sale = make_sale(quantity=4, unit_price="10.00", discount_pct="100")
        self.assertEqual(calculator.line_total(sale), Decimal("0.00"))


class DateFilterTest(unittest.TestCase):
    def setUp(self):
        self.sales = [
            make_sale(order_id="a", day=date(2026, 1, 31)),
            make_sale(order_id="b", day=date(2026, 2, 1)),
            make_sale(order_id="c", day=date(2026, 2, 28)),
            make_sale(order_id="d", day=date(2026, 3, 1)),
        ]

    def ids(self, sales):
        return [sale.order_id for sale in sales]

    def test_no_bounds_keeps_everything(self):
        self.assertEqual(self.ids(calculator.filter_by_date(self.sales)), ["a", "b", "c", "d"])

    def test_start_date_is_inclusive(self):
        kept = calculator.filter_by_date(self.sales, start=date(2026, 2, 1))
        self.assertEqual(self.ids(kept), ["b", "c", "d"])

    def test_end_date_is_inclusive(self):
        kept = calculator.filter_by_date(self.sales, end=date(2026, 2, 28))
        self.assertEqual(self.ids(kept), ["a", "b", "c"])

    def test_single_day_range_keeps_that_day(self):
        kept = calculator.filter_by_date(self.sales, start=date(2026, 2, 1), end=date(2026, 2, 1))
        self.assertEqual(self.ids(kept), ["b"])


class AggregationTest(unittest.TestCase):
    def test_total_revenue_sums_rounded_line_totals(self):
        sales = [
            make_sale(quantity=3, unit_price="2.50", discount_pct="15"),  # 6.38
            make_sale(quantity=3, unit_price="2.50", discount_pct="15"),  # 6.38
        ]
        self.assertEqual(calculator.total_revenue(sales), Decimal("12.76"))

    def test_total_revenue_of_nothing_is_zero(self):
        self.assertEqual(calculator.total_revenue([]), Decimal("0.00"))

    def test_order_count_counts_distinct_orders(self):
        sales = [make_sale(order_id="1"), make_sale(order_id="1"), make_sale(order_id="2")]
        self.assertEqual(calculator.order_count(sales), 2)

    def test_average_order_value_uses_distinct_orders_not_lines(self):
        # Order 1 has two lines (10 + 30), order 2 has one line (20).
        # Total 60 over 2 orders -> 30.00 (not 60 / 3 lines = 20.00).
        sales = [
            make_sale(order_id="1", unit_price="10.00"),
            make_sale(order_id="1", unit_price="30.00"),
            make_sale(order_id="2", unit_price="20.00"),
        ]
        self.assertEqual(calculator.average_order_value(sales), Decimal("30.00"))

    def test_average_order_value_of_nothing_is_zero(self):
        self.assertEqual(calculator.average_order_value([]), Decimal("0.00"))

    def test_revenue_by_region_is_sorted_by_name(self):
        sales = [make_sale(region="West"), make_sale(region="East"), make_sale(region="East")]
        result = calculator.revenue_by_region(sales)
        self.assertEqual(list(result.items()), [("East", Decimal("20.00")), ("West", Decimal("10.00"))])

    def test_revenue_by_month_groups_by_calendar_month(self):
        sales = [
            make_sale(day=date(2026, 2, 1)),
            make_sale(day=date(2026, 1, 31)),
            make_sale(day=date(2026, 1, 1)),
        ]
        result = calculator.revenue_by_month(sales)
        self.assertEqual(list(result.items()), [("2026-01", Decimal("20.00")), ("2026-02", Decimal("10.00"))])


class TopProductsTest(unittest.TestCase):
    def test_top_products_ranked_by_revenue_not_units(self):
        sales = [
            make_sale(product="Cable", quantity=50, unit_price="1.00"),     # 50 units, 50.00
            make_sale(product="Keyboard", quantity=2, unit_price="90.00"),  # 2 units, 180.00
            make_sale(product="Mouse", quantity=4, unit_price="20.00"),     # 4 units, 80.00
        ]
        result = calculator.top_products(sales, 2)
        self.assertEqual([entry["product"] for entry in result], ["Keyboard", "Mouse"])
        self.assertEqual(result[0], {"product": "Keyboard", "units_sold": 2, "revenue": Decimal("180.00")})

    def test_top_products_ties_broken_alphabetically(self):
        sales = [make_sale(product="Zeta"), make_sale(product="Alpha")]
        self.assertEqual([e["product"] for e in calculator.top_products(sales, 2)], ["Alpha", "Zeta"])

    def test_top_n_larger_than_product_count_returns_all(self):
        sales = [make_sale(product="A"), make_sale(product="B")]
        self.assertEqual(len(calculator.top_products(sales, 10)), 2)

    def test_top_products_combines_lines_of_same_product(self):
        sales = [make_sale(product="A", quantity=1), make_sale(product="A", quantity=2)]
        self.assertEqual(
            calculator.top_products(sales, 1),
            [{"product": "A", "units_sold": 3, "revenue": Decimal("30.00")}],
        )


if __name__ == "__main__":
    unittest.main()
