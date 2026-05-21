"""Stock information query module using AKShare."""

from dataclasses import dataclass
from datetime import date
from typing import List

import akshare as ak


@dataclass
class StockDailyBar:
    """Single day OHLCV bar."""
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


@dataclass
class StockProfile:
    """Stock basic profile."""
    code: str
    name: str
    full_name: str
    industry: str
    region: str
    main_business: str
    chairman: str
    market: str


def _to_market_prefix(stock_code: str) -> str:
    """
    Convert a bare stock code to Xueqiu-style market-prefixed symbol.

    Args:
        stock_code: Bare stock code, e.g. "000001"

    Returns:
        Prefixed symbol, e.g. "SZ000001"

    Raises:
        ValueError: If the code prefix is unrecognized
    """
    if stock_code.startswith(("60", "68")):
        return f"SH{stock_code}"
    if stock_code.startswith(("00", "30")):
        return f"SZ{stock_code}"
    if stock_code.startswith("8"):
        return f"BJ{stock_code}"
    raise ValueError(f"Cannot determine market for stock code: {stock_code}")


def _to_sina_symbol(stock_code: str) -> str:
    """
    Convert a bare stock code to Sina-style symbol.

    Args:
        stock_code: Bare stock code, e.g. "000001"

    Returns:
        Sina symbol, e.g. "sz000001"

    Raises:
        ValueError: If the code prefix is unrecognized
    """
    if stock_code.startswith(("60", "68")):
        return f"sh{stock_code}"
    if stock_code.startswith(("00", "30")):
        return f"sz{stock_code}"
    if stock_code.startswith("8"):
        return f"bj{stock_code}"
    raise ValueError(f"Cannot determine market for stock code: {stock_code}")


def get_stock_recent_bars(stock_code: str, days: int) -> List[StockDailyBar]:
    """
    Get recent N trading days of daily OHLCV data.

    Args:
        stock_code: Bare stock code, e.g. "000001"
        days: Number of recent trading days to fetch

    Returns:
        List of StockDailyBar, most recent last

    Raises:
        ValueError: If data cannot be fetched
    """
    sina_symbol = _to_sina_symbol(stock_code)
    end = date.today()
    start = date.fromordinal(end.toordinal() - days * 2)

    try:
        df = ak.stock_zh_a_daily(
            symbol=sina_symbol,
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="qfq",
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch daily bars for {stock_code}: {e}") from e

    if df.empty:
        raise ValueError(f"No daily data returned for {stock_code}")

    bars: List[StockDailyBar] = []
    for _, row in df.tail(days).iterrows():
        bars.append(StockDailyBar(
            date=row["date"],
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
            amount=float(row["amount"]),
        ))
    return bars


def get_stock_profile(stock_code: str) -> StockProfile:
    """
    Get stock profile including industry, region, and company info.

    Args:
        stock_code: Bare stock code, e.g. "000001"

    Returns:
        StockProfile with company details

    Raises:
        ValueError: If data cannot be fetched
    """
    xq_symbol = _to_market_prefix(stock_code)

    try:
        series = ak.stock_individual_basic_info_xq(symbol=xq_symbol)
    except Exception as e:
        raise ValueError(f"Failed to fetch profile for {stock_code}: {e}") from e

    values = series["value"]
    industry_raw = values.iloc[38] if len(values) > 38 else ""
    industry = ""
    if isinstance(industry_raw, dict):
        industry = industry_raw.get("ind_name", "")
    elif isinstance(industry_raw, str) and "ind_name" in industry_raw:
        import json
        industry = json.loads(industry_raw).get("ind_name", "")

    return StockProfile(
        code=stock_code,
        name=str(values.iloc[2]),
        full_name=str(values.iloc[1]),
        industry=industry,
        region=str(values.iloc[27]),
        main_business=str(values.iloc[5]).strip(),
        chairman=str(values.iloc[9]),
        market=_to_market_prefix(stock_code)[:2],
    )


def print_stock_summary(stock_code: str, days: int) -> None:
    """
    Print a formatted summary of stock profile and recent bars.

    Args:
        stock_code: Bare stock code, e.g. "000001"
        days: Number of recent trading days to display
    """
    profile = get_stock_profile(stock_code)
    bars = get_stock_recent_bars(stock_code, days)

    print(f"Stock: {profile.name} ({profile.code})")
    print(f"  Full Name : {profile.full_name}")
    print(f"  Market    : {profile.market}")
    print(f"  Industry  : {profile.industry}")
    print(f"  Region    : {profile.region}")
    print(f"  Chairman  : {profile.chairman}")
    print(f"  Business  : {profile.main_business[:80]}...")
    print()
    print(f"Recent {len(bars)} trading days:")
    print(f"{'Date':>12}  {'Open':>8}  {'High':>8}  {'Low':>8}  {'Close':>8}  {'Volume':>12}")
    print("-" * 68)
    for bar in bars:
        print(
            f"{bar.date!s:>12}  {bar.open:>8.2f}  {bar.high:>8.2f}  "
            f"{bar.low:>8.2f}  {bar.close:>8.2f}  {bar.volume:>12,}"
        )