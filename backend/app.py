"""FastAPI backend for SmartStock."""

import json
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.core.portfolio import get_portfolio_summary, get_realtime_price, normalize_code
from backend.core.portfolio_db import (
    create_portfolio,
    delete_portfolio,
    get_portfolio,
    get_pnl_history,
    get_trades,
    init_db,
    list_portfolios,
    record_trade,
    update_portfolio,
)
from backend.core.scan_limit_up import scan_and_predict, scan_and_predict_with_progress
from backend.core.stock_links import get_stock_links


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="SmartStock API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
)


@app.get("/api/limit-up")
def get_limit_up():
    """Return today's limit-up stocks with predictions."""
    try:
        predictions = scan_and_predict()
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "date": date.today().isoformat(),
        "count": len(predictions),
        "predictions": [asdict(p) for p in predictions],
    }


@app.get("/api/limit-up/stream")
def stream_limit_up():
    """Stream limit-up scan progress via SSE, then send final result."""

    def event_stream():
        gen = scan_and_predict_with_progress()
        try:
            while True:
                current, total, code, name = next(gen)
                data = json.dumps({
                    "type": "progress",
                    "current": current,
                    "total": total,
                    "code": code,
                    "name": name,
                }, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except StopIteration as e:
            predictions = e.value if e.value else []
            data = json.dumps({
                "type": "done",
                "date": date.today().isoformat(),
                "count": len(predictions),
                "predictions": [asdict(p) for p in predictions],
            }, ensure_ascii=False)
            yield f"data: {data}\n\n"
        except ValueError as e:
            data = json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/stock-links")
def stock_links(code: str):
    """Return community links for a stock by code or name."""
    try:
        result = get_stock_links(code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return asdict(result)


# ---------- Portfolio Simulation ----------

class PortfolioCreate(BaseModel):
    name: str
    initial_cash: float


class PortfolioUpdate(BaseModel):
    name: str


class TradeCreate(BaseModel):
    stock_code: str
    stock_name: str
    trade_type: str
    price: float
    quantity: int


@app.get("/api/portfolios")
def api_list_portfolios():
    """List all portfolios."""
    return list_portfolios()


@app.post("/api/portfolios")
def api_create_portfolio(body: PortfolioCreate):
    """Create a new portfolio."""
    pid = create_portfolio(body.name, body.initial_cash)
    return get_portfolio(pid)


@app.get("/api/portfolios/{portfolio_id}")
def api_get_portfolio(portfolio_id: int):
    """Get portfolio detail."""
    try:
        return get_portfolio(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/portfolios/{portfolio_id}")
def api_update_portfolio(portfolio_id: int, body: PortfolioUpdate):
    """Update portfolio name."""
    try:
        get_portfolio(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    update_portfolio(portfolio_id, body.name)
    return get_portfolio(portfolio_id)


@app.delete("/api/portfolios/{portfolio_id}")
def api_delete_portfolio(portfolio_id: int):
    """Delete a portfolio and its trades/holdings."""
    try:
        get_portfolio(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    delete_portfolio(portfolio_id)
    return {"ok": True}


@app.get("/api/portfolios/{portfolio_id}/summary")
def api_portfolio_summary(portfolio_id: int):
    """Get portfolio summary with real-time P&L."""
    try:
        summary = get_portfolio_summary(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return asdict(summary)


@app.post("/api/portfolios/{portfolio_id}/trades")
def api_create_trade(portfolio_id: int, body: TradeCreate):
    """Execute a buy or sell trade."""
    try:
        code = normalize_code(body.stock_code)
        trade = record_trade(
            portfolio_id, code, body.stock_name,
            body.trade_type, body.price, body.quantity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return trade


@app.get("/api/portfolios/{portfolio_id}/trades")
def api_list_trades(portfolio_id: int):
    """List trade history for a portfolio."""
    return get_trades(portfolio_id)


@app.get("/api/portfolios/{portfolio_id}/pnl-history")
def api_pnl_history(portfolio_id: int):
    """Get P&L history after each trade for charting."""
    try:
        return get_pnl_history(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/stock-price")
def api_stock_price(code: str):
    """Get real-time stock price."""
    try:
        quote = get_realtime_price(code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return asdict(quote)