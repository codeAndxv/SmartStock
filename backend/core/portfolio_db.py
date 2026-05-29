"""SQLite database layer for portfolio simulation."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(__file__).parent.parent / "portfolio.db"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def _conn():
    """Yield a connection with auto-commit/rollback."""
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    except BaseException:
        c.rollback()
        raise
    finally:
        c.close()


def init_db() -> None:
    """Create tables if they don't exist."""
    with _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                initial_cash REAL   NOT NULL,
                created_at  TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS holdings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                stock_code   TEXT    NOT NULL,
                stock_name   TEXT    NOT NULL,
                quantity     INTEGER NOT NULL DEFAULT 0,
                avg_cost     REAL    NOT NULL DEFAULT 0,
                UNIQUE(portfolio_id, stock_code)
            );
            CREATE TABLE IF NOT EXISTS trades (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
                stock_code   TEXT    NOT NULL,
                stock_name   TEXT    NOT NULL,
                trade_type   TEXT    NOT NULL CHECK(trade_type IN ('buy', 'sell')),
                price        REAL    NOT NULL,
                quantity     INTEGER NOT NULL,
                amount       REAL    NOT NULL,
                created_at   TEXT    NOT NULL
            );
        """)


# ---------- Portfolio CRUD ----------

def create_portfolio(name: str, initial_cash: float) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO portfolios (name, initial_cash, created_at) VALUES (?, ?, ?)",
            (name, initial_cash, _now()),
        )
        return cur.lastrowid


def list_portfolios() -> List[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM portfolios ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]


def get_portfolio(portfolio_id: int) -> dict:
    with _conn() as c:
        row = c.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone()
        if not row:
            raise ValueError(f"Portfolio not found: {portfolio_id}")
        return dict(row)


def update_portfolio(portfolio_id: int, name: str) -> None:
    with _conn() as c:
        c.execute("UPDATE portfolios SET name = ? WHERE id = ?", (name, portfolio_id))


def delete_portfolio(portfolio_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM portfolios WHERE id = ?", (portfolio_id,))


# ---------- Holdings ----------

def get_holdings(portfolio_id: int) -> List[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM holdings WHERE portfolio_id = ? AND quantity > 0 ORDER BY stock_code",
            (portfolio_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _upsert_holding(c: sqlite3.Connection, portfolio_id: int, stock_code: str,
                    stock_name: str, quantity: int, avg_cost: float) -> None:
    existing = c.execute(
        "SELECT id, quantity, avg_cost FROM holdings WHERE portfolio_id = ? AND stock_code = ?",
        (portfolio_id, stock_code),
    ).fetchone()

    if existing:
        c.execute(
            "UPDATE holdings SET quantity = ?, avg_cost = ?, stock_name = ? WHERE id = ?",
            (quantity, avg_cost, stock_name, existing["id"]),
        )
    else:
        c.execute(
            "INSERT INTO holdings (portfolio_id, stock_code, stock_name, quantity, avg_cost) VALUES (?, ?, ?, ?, ?)",
            (portfolio_id, stock_code, stock_name, quantity, avg_cost),
        )


# ---------- Trades ----------

def record_trade(portfolio_id: int, stock_code: str, stock_name: str,
                 trade_type: str, price: float, quantity: int) -> dict:
    """Execute a buy or sell trade and update holdings.

    Returns the created trade record.

    Raises:
        ValueError: If insufficient shares to sell or insufficient cash to buy
    """
    amount = price * quantity

    with _conn() as c:
        portfolio = c.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone()
        if not portfolio:
            raise ValueError(f"Portfolio not found: {portfolio_id}")

        holding = c.execute(
            "SELECT * FROM holdings WHERE portfolio_id = ? AND stock_code = ?",
            (portfolio_id, stock_code),
        ).fetchone()

        if trade_type == "buy":
            # Check cash: initial_cash + realized gains from sells - spent on buys
            total_spent = c.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM trades WHERE portfolio_id = ? AND trade_type = 'buy'",
                (portfolio_id,),
            ).fetchone()[0]
            total_received = c.execute(
                "SELECT COALESCE(SUM(amount), 0) FROM trades WHERE portfolio_id = ? AND trade_type = 'sell'",
                (portfolio_id,),
            ).fetchone()[0]
            available_cash = portfolio["initial_cash"] - total_spent + total_received
            if amount > available_cash:
                raise ValueError(f"Insufficient cash: need {amount:.2f}, have {available_cash:.2f}")

            if holding:
                old_qty = holding["quantity"]
                old_cost = holding["avg_cost"]
                new_qty = old_qty + quantity
                new_avg = (old_cost * old_qty + price * quantity) / new_qty
                _upsert_holding(c, portfolio_id, stock_code, stock_name, new_qty, new_avg)
            else:
                _upsert_holding(c, portfolio_id, stock_code, stock_name, quantity, price)

        elif trade_type == "sell":
            if not holding or holding["quantity"] < quantity:
                have = holding["quantity"] if holding else 0
                raise ValueError(f"Insufficient shares: need {quantity}, have {have}")

            new_qty = holding["quantity"] - quantity
            _upsert_holding(c, portfolio_id, stock_code, stock_name, new_qty, holding["avg_cost"])

        else:
            raise ValueError(f"Invalid trade type: {trade_type}")

        cur = c.execute(
            "INSERT INTO trades (portfolio_id, stock_code, stock_name, trade_type, price, quantity, amount, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (portfolio_id, stock_code, stock_name, trade_type, price, quantity, amount, _now()),
        )
        trade_id = cur.lastrowid

    return {
        "id": trade_id,
        "portfolio_id": portfolio_id,
        "stock_code": stock_code,
        "stock_name": stock_name,
        "trade_type": trade_type,
        "price": price,
        "quantity": quantity,
        "amount": amount,
        "created_at": _now(),
    }


def get_trades(portfolio_id: int) -> List[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM trades WHERE portfolio_id = ? ORDER BY created_at DESC",
            (portfolio_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_pnl_history(portfolio_id: int) -> List[dict]:
    """Reconstruct P&L after each trade for charting.

    Returns list of {time, trade_type, stock_name, realized_pnl, total_pnl, pnl_pct}
    ordered chronologically.
    """
    with _conn() as c:
        portfolio = c.execute("SELECT * FROM portfolios WHERE id = ?", (portfolio_id,)).fetchone()
        if not portfolio:
            raise ValueError(f"Portfolio not found: {portfolio_id}")

        trades = c.execute(
            "SELECT * FROM trades WHERE portfolio_id = ? ORDER BY created_at ASC, id ASC",
            (portfolio_id,),
        ).fetchall()

    initial_cash = portfolio["initial_cash"]
    # holdings: {stock_code: {qty, avg_cost, name}}
    holdings: dict = {}
    cumulative_realized = 0.0
    history: List[dict] = []

    for t in trades:
        code = t["stock_code"]
        price = t["price"]
        qty = t["quantity"]
        amount = t["amount"]

        if t["trade_type"] == "buy":
            if code in holdings:
                h = holdings[code]
                new_qty = h["qty"] + qty
                new_avg = (h["avg_cost"] * h["qty"] + price * qty) / new_qty
                h["qty"] = new_qty
                h["avg_cost"] = new_avg
            else:
                holdings[code] = {"qty": qty, "avg_cost": price, "name": t["stock_name"]}
        elif t["trade_type"] == "sell":
            if code in holdings:
                h = holdings[code]
                realized = (price - h["avg_cost"]) * qty
                cumulative_realized += realized
                h["qty"] -= qty
                if h["qty"] <= 0:
                    del holdings[code]

        # total cost of current holdings
        held_cost = sum(h["avg_cost"] * h["qty"] for h in holdings.values())
        total_pnl = cumulative_realized + (0.0)  # realized only; no live market data here
        pnl_pct = (cumulative_realized / initial_cash * 100) if initial_cash > 0 else 0.0

        history.append({
            "time": t["created_at"],
            "trade_type": t["trade_type"],
            "stock_name": t["stock_name"],
            "price": price,
            "quantity": qty,
            "realized_pnl": round(cumulative_realized, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    return history
