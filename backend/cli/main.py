"""Example script demonstrating stock information queries."""

import sys

from backend.core.stock_info import print_stock_summary


def main() -> None:
    """Query a stock and display its profile and recent bars."""
    stock_code = "000001"
    days = 10

    if len(sys.argv) >= 2:
        stock_code = sys.argv[1]
    if len(sys.argv) >= 3:
        days = int(sys.argv[2])

    print_stock_summary(stock_code, days)


if __name__ == "__main__":
    main()