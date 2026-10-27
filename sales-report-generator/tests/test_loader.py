"""Tests for reading and validating the input CSV."""

import unittest
from datetime import date
from decimal import Decimal

from sales_report.loader import SalesDataError, load_sales, normalize_region
from tests.helpers import TempCsvMixin


class LoadValidRowsTest(TempCsvMixin, unittest.TestCase):
    def test_valid_row_is_parsed_into_typed_fields(self):
        path = self.write_csv("1001,2026-01-05,North,Keyboard,2,89.00,10")
        sales, skipped = load_sales(path)
        self.assertEqual(skipped, [])
        self.assertEqual(len(sales), 1)
        sale = sales[0]
        self.assertEqual(sale.order_id, "1001")
        self.assertEqual(sale.sale_date, date(2026, 1, 5))
        self.assertEqual(sale.quantity, 2)
        self.assertEqual(sale.unit_price, Decimal("89.00"))
        self.assertEqual(sale.discount_pct, Decimal("10"))

    def test_blank_discount_defaults_to_zero(self):
        path = self.write_csv("1,2026-01-05,North,Keyboard,1,89.00,")
        sales, _ = load_sales(path)
        self.assertEqual(sales[0].discount_pct, Decimal("0"))

    def test_discount_column_is_optional(self):
        path = self.write_csv(
            "1,2026-01-05,North,Keyboard,1,89.00",
            header="order_id,date,region,product,quantity,unit_price",
        )
        sales, skipped = load_sales(path)
        self.assertEqual((len(sales), skipped), (1, []))

    def test_headers_with_spaces_are_accepted(self):
        path = self.write_csv(
            "1,2026-01-05,North,Keyboard,1,89.00,0",
            header=" order_id , date , region , product , quantity , unit_price , discount_pct ",
        )
        sales, skipped = load_sales(path)
        self.assertEqual((len(sales), skipped), (1, []))


class RegionNormalizationTest(TempCsvMixin, unittest.TestCase):
    def test_normalize_region_is_case_and_whitespace_insensitive(self):
        for raw in ("North", "north", "NORTH", "  north  "):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_region(raw), "North")

    def test_normalize_region_collapses_inner_spaces(self):
        self.assertEqual(normalize_region("south   east"), "South East")

    def test_region_spellings_load_as_one_region(self):
        path = self.write_csv(
            "1,2026-01-05,North,A,1,1.00,0",
            "2,2026-01-06,north,A,1,1.00,0",
            "3,2026-01-07,NORTH,A,1,1.00,0",
        )
        sales, _ = load_sales(path)
        self.assertEqual({sale.region for sale in sales}, {"North"})


class InvalidRowsAreSkippedTest(TempCsvMixin, unittest.TestCase):
    """Bad rows must be skipped with a reason, never crash the program."""

    def assert_single_row_skipped(self, row, reason_fragment):
        path = self.write_csv(row)
        sales, skipped = load_sales(path)
        self.assertEqual(sales, [], "invalid row should not be loaded")
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0].line, 2)
        self.assertIn(reason_fragment, skipped[0].reason)

    def test_zero_quantity_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,0,10.00,0", "quantity")

    def test_negative_quantity_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,-3,10.00,0", "quantity")

    def test_non_integer_quantity_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,two,10.00,0", "quantity")

    def test_non_numeric_unit_price_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,1,N/A,0", "unit_price")

    def test_non_numeric_discount_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,1,10.00,ten", "discount_pct")

    def test_nan_unit_price_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,1,NaN,0", "unit_price")

    def test_negative_unit_price_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,1,-1.00,0", "unit_price")

    def test_discount_above_100_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,A,1,10.00,120", "discount_pct")

    def test_impossible_date_is_skipped(self):
        self.assert_single_row_skipped("1,2026-02-30,North,A,1,10.00,0", "date")

    def test_wrong_date_format_is_skipped(self):
        self.assert_single_row_skipped("1,05/18/2026,North,A,1,10.00,0", "date")

    def test_empty_product_is_skipped(self):
        self.assert_single_row_skipped("1,2026-01-05,North,,1,10.00,0", "product")

    def test_valid_rows_after_a_bad_row_still_load(self):
        path = self.write_csv(
            "1,2026-01-05,North,A,1,N/A,0",
            "2,2026-01-06,North,B,1,5.00,0",
        )
        sales, skipped = load_sales(path)
        self.assertEqual([sale.order_id for sale in sales], ["2"])
        self.assertEqual([row.line for row in skipped], [2])


class UnusableFileTest(TempCsvMixin, unittest.TestCase):
    def test_missing_required_column_raises(self):
        path = self.write_csv("1,2026-01-05,North,A,1", header="order_id,date,region,product,quantity")
        with self.assertRaises(SalesDataError) as ctx:
            load_sales(path)
        self.assertIn("unit_price", str(ctx.exception))

    def test_completely_empty_file_raises(self):
        path = self.write_csv(header="")
        with self.assertRaises(SalesDataError):
            load_sales(path)

    def test_header_only_file_loads_nothing(self):
        path = self.write_csv()
        self.assertEqual(load_sales(path), ([], []))


if __name__ == "__main__":
    unittest.main()
