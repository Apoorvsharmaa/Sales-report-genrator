"""Allow running the application with ``python -m sales_report``."""

from sales_report.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
