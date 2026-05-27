"""Portfolio simulation business logic."""

from dataclasses import dataclass
from typing import Dict, List

import akshare as ak

from backend.core.stock_info import _to_market_prefix


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
    """Fetch real-time quotes for a list of stock codes.

    Args:
        codes: List of 6-digit stock codes

    Returns:
        Dict mapping code to StockQuote (empty if fetch fails)
    """
    if not codes:
        return {}

    try:
        df = ak.stock_zh_a_spot_em()
    except Exception:
        return {}

    df["代码"] = df["代码"].astype(str).str.zfill(6)
    filtered = df[df["代码"].isin(codes)]

    quotes: Dict[str, StockQuote] = {}
    for _, row in filtered.iterrows():
        code = str(row["代码"])
        price = float(row["最新价"]) if row["最新价"] else 0.0
        change_pct = float(row["涨跌幅"]) if row["涨跌幅"] else 0.0
        open_p = float(row["今开"]) if row["今开"] else 0.0
        high = float(row["最高"]) if row["最高"] else 0.0
        low = float(row["最低"]) if row["最低"] else 0.0
        quotes[code] = StockQuote(
            code=code,
            name=str(row["名称"]),
            price=price,
            change_pct=change_pct,
            open=open_p,
            high=high,
            low=low,
        )
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

    total_unrealized = total_market_value - total_cost
    total_pnl_pct = (total_unrealized / total_cost * 100) if total_cost > 0 else 0.0

    return PortfolioSummary(
        id=p["id"],
        name=p["name"],
        initial_cash=p["initial_cash"],
        total_cost=round(total_cost, 2),
        total_market_value=round(total_market_value, 2),
        total_unrealized_pnl=round(total_unrealized, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        cash_remaining=round(cash_remaining, 2),
        holdings=holding_views,
    )


def get_realtime_price(stock_code: str) -> StockQuote:
    """Get real-time quote for a single stock.

    Args:
        stock_code: 6-digit stock code

    Returns:
        StockQuote with current price

    Raises:
        ValueError: If stock not found
    """
    quotes = _fetch_quotes([stock_code])
    if stock_code not in quotes:
        raise ValueError(f"Stock not found or no price data: {stock_code}")
    return quotes[stock_code]
