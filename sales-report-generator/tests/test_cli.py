"""End-to-end tests: run the real command and compare against expected output files."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from sales_report.cli import main
from tests.helpers import DATA_DIR, EXPECTED_DIR, TempCsvMixin

SAMPLE = os.path.join(DATA_DIR, "sample_sales.csv")
MESSY = os.path.join(DATA_DIR, "messy_sales.csv")


def run_cli(*args):
    """Run main() and capture (exit_code, stdout, stderr). argparse errors are captured too."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = main(list(args))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def read_expected(name):
    with open(os.path.join(EXPECTED_DIR, name), encoding="utf-8") as handle:
        return handle.read()


class ExpectedOutputTest(unittest.TestCase):
    """The committed files in expected_output/ are the source of truth."""

    def assert_matches_expected_json(self, expected_file, *args):
        code, out, err = run_cli(*args)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out), json.loads(read_expected(expected_file)))

    def test_sample_json_report(self):
        self.assert_matches_expected_json("sample_report.json", SAMPLE, "--top", "3")

    def test_sample_text_report(self):
        code, out, err = run_cli(SAMPLE, "--top", "3", "--format", "text")
        self.assertEqual(code, 0, err)
        self.assertEqual(out, read_expected("sample_report.txt"))

    def test_q1_date_filtered_report(self):
        self.assert_matches_expected_json(
            "q1_report.json", SAMPLE, "--start-date", "2026-01-01", "--end-date", "2026-03-31"
        )

    def test_messy_input_report(self):
        self.assert_matches_expected_json("messy_report.json", MESSY)


class CliBehaviourTest(TempCsvMixin, unittest.TestCase):
    def test_output_file_option_writes_report(self):
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "report.json")
            code, out, err = run_cli(SAMPLE, "--output", target)
            self.assertEqual(code, 0, err)
            self.assertEqual(out, "")
            with open(target, encoding="utf-8") as handle:
                self.assertIn("total_revenue", json.load(handle)["summary"])

    def test_missing_input_file_exits_2_with_message(self):
        code, out, err = run_cli(os.path.join(DATA_DIR, "does_not_exist.csv"))
        self.assertEqual(code, 2)
        self.assertIn("Error:", err)
        self.assertNotIn("Traceback", err)

    def test_missing_required_column_exits_2(self):
        path = self.write_csv("1,2026-01-05", header="order_id,date")
        code, _, err = run_cli(path)
        self.assertEqual(code, 2)
        self.assertIn("missing required column", err)

    def test_top_must_be_positive(self):
        code, _, _ = run_cli(SAMPLE, "--top", "0")
        self.assertEqual(code, 2)

    def test_invalid_date_argument_exits_2(self):
        code, _, _ = run_cli(SAMPLE, "--start-date", "31-01-2026")
        self.assertEqual(code, 2)

    def test_start_after_end_exits_2(self):
        code, _, _ = run_cli(SAMPLE, "--start-date", "2026-03-01", "--end-date", "2026-02-01")
        self.assertEqual(code, 2)

    def test_header_only_file_produces_empty_report(self):
        path = self.write_csv()
        code, out, err = run_cli(path)
        self.assertEqual(code, 0, err)
        summary = json.loads(out)["summary"]
        self.assertEqual(summary["total_revenue"], "0.00")
        self.assertEqual(summary["average_order_value"], "0.00")
        self.assertIsNone(summary["first_sale_date"])

    def test_filter_that_matches_nothing_produces_empty_report(self):
        code, out, err = run_cli(SAMPLE, "--start-date", "2030-01-01")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["summary"]["order_count"], 0)


if __name__ == "__main__":
    unittest.main()
