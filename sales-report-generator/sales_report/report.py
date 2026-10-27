"""Assemble calculation results into a report and render it as JSON or text."""

import json

from sales_report import calculator


def _money(value):
    return f"{value:.2f}"


def build_report(sales, skipped, top_n=3, start=None, end=None):
    """Build the report as a plain dict (money values are strings like "12.50")."""
    selected = calculator.filter_by_date(sales, start, end)

    if selected:
        first = min(sale.sale_date for sale in selected).isoformat()
        last = max(sale.sale_date for sale in selected).isoformat()
    else:
        first = last = None

    return {
        "filters": {
            "start_date": start.isoformat() if start else None,
            "end_date": end.isoformat() if end else None,
        },
        "summary": {
            "total_revenue": _money(calculator.total_revenue(selected)),
            "order_count": calculator.order_count(selected),
            "line_item_count": len(selected),
            "units_sold": calculator.total_units(selected),
            "average_order_value": _money(calculator.average_order_value(selected)),
            "first_sale_date": first,
            "last_sale_date": last,
        },
        "revenue_by_region": {
            region: _money(amount)
            for region, amount in calculator.revenue_by_region(selected).items()
        },
        "revenue_by_month": {
            month: _money(amount)
            for month, amount in calculator.revenue_by_month(selected).items()
        },
        "top_products": [
            {
                "product": entry["product"],
                "units_sold": entry["units_sold"],
                "revenue": _money(entry["revenue"]),
            }
            for entry in calculator.top_products(selected, top_n)
        ],
        "skipped_rows": [{"line": row.line, "reason": row.reason} for row in skipped],
    }


def render_json(report):
    """Render the report as pretty-printed JSON (ends with a newline)."""
    return json.dumps(report, indent=2) + "\n"


def render_text(report):
    """Render the report as a human-readable plain-text summary."""
    summary = report["summary"]
    filters = report["filters"]
    lines = [
        "SALES REPORT",
        "============",
        f"Date filter       : {filters['start_date'] or 'any'} to {filters['end_date'] or 'any'}",
        f"Sales period      : {summary['first_sale_date'] or '-'} to {summary['last_sale_date'] or '-'}",
        f"Total revenue     : {summary['total_revenue']}",
        f"Orders            : {summary['order_count']}",
        f"Line items        : {summary['line_item_count']}",
        f"Units sold        : {summary['units_sold']}",
        f"Avg order value   : {summary['average_order_value']}",
        "",
        "Revenue by region",
        "-----------------",
    ]
    lines += [f"  {region:<16}{amount:>12}" for region, amount in report["revenue_by_region"].items()]
    lines += ["", "Revenue by month", "----------------"]
    lines += [f"  {month:<16}{amount:>12}" for month, amount in report["revenue_by_month"].items()]
    lines += ["", "Top products", "------------"]
    for rank, entry in enumerate(report["top_products"], start=1):
        lines.append(
            f"  {rank}. {entry['product']:<20}{entry['revenue']:>12}  ({entry['units_sold']} units)"
        )
    lines += ["", f"Skipped rows: {len(report['skipped_rows'])}"]
    lines += [f"  line {row['line']}: {row['reason']}" for row in report["skipped_rows"]]
    return "\n".join(lines) + "\n"
