"""Command-line interface.

Exit codes:
    0  report generated successfully
    2  bad arguments or unusable input file (message printed to stderr)
"""

import argparse
import sys
from datetime import datetime

from sales_report.loader import DATE_FORMAT, SalesDataError, load_sales
from sales_report.report import build_report, render_json, render_text


def _date_arg(value):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from None


def _positive_int(value):
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a whole number, got {value!r}") from None
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {number}")
    return number


def build_parser():
    parser = argparse.ArgumentParser(
        prog="sales_report",
        description="Generate a revenue report from a CSV file of sales line items.",
    )
    parser.add_argument("input", help="path to the sales CSV file")
    parser.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    parser.add_argument(
        "-f", "--format", choices=("json", "text"), default="json", help="output format (default: json)"
    )
    parser.add_argument(
        "--top", type=_positive_int, default=3, help="number of top products to list (default: 3)"
    )
    parser.add_argument("--start-date", type=_date_arg, help="include sales on or after this date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=_date_arg, help="include sales on or before this date (YYYY-MM-DD)")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.start_date and args.end_date and args.start_date > args.end_date:
        parser.error("--start-date must not be after --end-date")

    try:
        sales, skipped = load_sales(args.input)
    except SalesDataError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    report = build_report(sales, skipped, top_n=args.top, start=args.start_date, end=args.end_date)
    output = render_text(report) if args.format == "text" else render_json(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)
    return 0
