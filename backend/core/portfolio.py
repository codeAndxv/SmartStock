"""Portfolio simulation business logic."""

from dataclasses import dataclass
from typing import Dict, List

import re

import requests

from backend.core.stock_info import _to_sina_symbol

_PREFIX_RE = re.compile(r"^(?:sh|sz|bj)?(\d{6})$", re.IGNORECASE)


def normalize_code(raw: str) -> str:
    """Normalize stock code input to bare 6-digit code.

    Accepts: "000001", "SZ000725", "sz000725", "SH600519", "bj830001"
    """
    m = _PREFIX_RE.match(raw.strip())
    if m:
        return m.group(1)
    if raw.strip().isdigit() and len(raw.strip()) == 6:
        return raw.strip()
    raise ValueError(f"Invalid stock code format: {raw}")


@dataclass
class StockQuote:
    """Real-time stock quote."""
    code: str
    name: str
    price: float
    change_pct: float
    open: float
    high: float
    low: float


@dataclass
class HoldingView:
    """Holding with current market value and P&L."""
    stock_code: str
    stock_name: str
    quantity: int
    avg_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class PortfolioSummary:
    """Full portfolio summary with P&L."""
    id: int
    name: str
    initial_cash: float
    total_cost: float
    total_market_value: float
    total_unrealized_pnl: float
    total_pnl_pct: float
    cash_remaining: float
    holdings: List[HoldingView]


def _fetch_quotes(codes: List[str]) -> Dict[str, StockQuote]:
    """Fetch real-time quotes via Sina HTTP API (fast, per-stock).

    Args:
        codes: List of 6-digit stock codes

    Returns:
        Dict mapping code to StockQuote (empty if fetch fails)
    """
    if not codes:
        return {}

    sina_symbols = []
    sina_to_code: Dict[str, str] = {}
    for code in codes:
        try:
            s = _to_sina_symbol(code)
            sina_symbols.append(s)
            sina_to_code[s] = code
        except ValueError:
            continue

    if not sina_symbols:
        return {}

    url = f"https://hq.sinajs.cn/list={','.join(sina_symbols)}"
    try:
        r = requests.get(url, headers={"Referer": "https://finance.sina.com.cn"}, timeout=5)
        r.raise_for_status()
    except Exception:
        return {}

    quotes: Dict[str, StockQuote] = {}
    for line in r.text.strip().split("\n"):
        if "=" not in line:
            continue
        symbol_part, _, data_part = line.partition("=")
        symbol = symbol_part.split("_")[-1].strip('"')
        code = sina_to_code.get(symbol)
        if not code:
            continue

        fields = data_part.strip('";\n').split(",")
        if len(fields) < 6:
            continue

        try:
            name = fields[0]
            prev_close = float(fields[2]) if fields[2] else 0.0
            price = float(fields[3]) if fields[3] else 0.0
            high = float(fields[4]) if fields[4] else 0.0
            low = float(fields[5]) if fields[5] else 0.0
            open_p = float(fields[1]) if fields[1] else 0.0
            change_pct = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
            quotes[code] = StockQuote(
                code=code,
                name=name,
                price=price,
                change_pct=round(change_pct, 2),
                open=open_p,
                high=high,
                low=low,
            )
        except (ValueError, IndexError):
            continue

    return quotes


def get_portfolio_summary(portfolio_id: int) -> PortfolioSummary:
    """Calculate portfolio summary with real-time P&L.

    Args:
        portfolio_id: Portfolio ID

    Returns:
        PortfolioSummary with holdings and P&L

    Raises:
        ValueError: If portfolio not found or data fetch fails
    """
    from backend.core.portfolio_db import get_holdings, get_portfolio, get_trades

    p = get_portfolio(portfolio_id)
    holdings = get_holdings(portfolio_id)
    trades = get_trades(portfolio_id)

    codes = [h["stock_code"] for h in holdings]
    quotes = _fetch_quotes(codes)

    total_sell = sum(t["amount"] for t in trades if t["trade_type"] == "sell")
    total_buy = sum(t["amount"] for t in trades if t["trade_type"] == "buy")
    cash_remaining = p["initial_cash"] - total_buy + total_sell

    holding_views: List[HoldingView] = []
    total_cost = 0.0
    total_market_value = 0.0

    for h in holdings:
        code = h["stock_code"]
        qty = h["quantity"]
        avg_cost = h["avg_cost"]
        quote = quotes.get(code)
        current_price = quote.price if quote else avg_cost

        cost_basis = avg_cost * qty
        market_value = current_price * qty
        unrealized_pnl = market_value - cost_basis
        pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0

        total_cost += cost_basis
        total_market_value += market_value

        holding_views.append(HoldingView(
            stock_code=code,
            stock_name=h["stock_name"],
            quantity=qty,
            avg_cost=round(avg_cost, 3),
            current_price=round(current_price, 2),
            market_value=round(market_value, 2),
            cost_basis=round(cost_basis, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            unrealized_pnl_pct=round(pnl_pct, 2),
        ))

    total_pnl = (total_market_value + cash_remaining) - p["initial_cash"]
    total_pnl_pct = (total_pnl / p["initial_cash"] * 100) if p["initial_cash"] > 0 else 0.0

    return PortfolioSummary(
        id=p["id"],
        name=p["name"],
        initial_cash=p["initial_cash"],
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_unrealized_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        cash_remaining=round(cash_remaining, 2),
        holdings=holding_views,
    )


def get_realtime_price(stock_code: str) -> StockQuote:
    """Get real-time quote for a single stock.

    Args:
        stock_code: Stock code (bare "000001" or prefixed "SZ000001")

    Returns:
        StockQuote with current price

    Raises:
        ValueError: If stock not found
    """
    code = normalize_code(stock_code)
    quotes = _fetch_quotes([code])
    if code not in quotes:
        raise ValueError(f"Stock not found or no price data: {stock_code}")
    return quotes[code]
