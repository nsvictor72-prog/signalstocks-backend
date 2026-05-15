"""
Portfolio / Paper Trading API
- POST /api/portfolio/paper   — create a paper trade from a signal
- GET  /api/portfolio         — list current user's positions
- POST /api/portfolio/{id}/close — close a position
- DELETE /api/portfolio/{id}  — delete a position
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from database import Portfolio, Stock
from routers.auth import get_current_user, get_db

router = APIRouter()

PAPER_POSITION_SIZE = 10_000   # $10k default per paper trade
STOP_LOSS_PCT       = 0.08     # -8%
TAKE_PROFIT_PCT     = 0.12     # +12%


# ── Request bodies ────────────────────────────────────────────────────────────

class PaperTradeRequest(BaseModel):
    ticker: str
    entry_price: float
    signal_type: str
    stop_loss: float | None = None
    take_profit: float | None = None
    notes: str | None = None


class CloseRequest(BaseModel):
    exit_price: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def _serialize(pos: Portfolio, ticker: str, company: str) -> dict:
    cost = pos.shares * pos.entry_price
    return {
        "id":              pos.id,
        "ticker":          ticker,
        "company":         company or ticker,
        "is_paper_trade":  pos.is_paper_trade,
        "is_open":         pos.is_open,
        "shares":          pos.shares,
        "entry_price":     pos.entry_price,
        "entry_date":      pos.entry_date.isoformat() if pos.entry_date else None,
        "stop_loss_price": pos.stop_loss_price,
        "take_profit_price": pos.take_profit_price,
        "exit_price":      pos.exit_price,
        "exit_date":       pos.exit_date.isoformat() if pos.exit_date else None,
        "position_value":  cost,
        "realized_pnl":    pos.realized_pnl,
        "realized_pnl_pct":pos.realized_pnl_pct,
        "notes":           pos.notes,
        "signal_type":     pos.notes.split("|")[0].strip() if pos.notes else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/portfolio/paper", status_code=201)
def create_paper_trade(
    body: PaperTradeRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stock = db.query(Stock).filter(Stock.ticker == body.ticker.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Ticker '{body.ticker}' not found in universe")

    shares = max(1, int(PAPER_POSITION_SIZE / body.entry_price))
    stop   = body.stop_loss   or round(body.entry_price * (1 - STOP_LOSS_PCT), 2)
    target = body.take_profit or round(body.entry_price * (1 + TAKE_PROFIT_PCT), 2)

    pos = Portfolio(
        stock_id         = stock.id,
        user_id          = current_user.id,
        entry_date       = datetime.utcnow(),
        entry_price      = body.entry_price,
        shares           = shares,
        position_value   = shares * body.entry_price,
        is_open          = True,
        is_paper_trade   = True,
        stop_loss_price  = stop,
        take_profit_price= target,
        notes            = f"{body.signal_type} | {body.notes or 'Paper trade from Orders page'}",
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)

    return {
        "message": f"Paper trade created: {shares} shares of {body.ticker.upper()} @ ${body.entry_price:.2f}",
        "position": _serialize(pos, stock.ticker, stock.company_name or stock.ticker),
    }


@router.get("/portfolio")
def get_portfolio(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Portfolio, Stock.ticker, Stock.company_name)
        .join(Stock, Portfolio.stock_id == Stock.id)
        .filter(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.entry_date.desc())
        .all()
    )

    open_positions   = [_serialize(p, t, c) for p, t, c in rows if p.is_open]
    closed_positions = [_serialize(p, t, c) for p, t, c in rows if not p.is_open]

    paper_realized = sum(
        (p.realized_pnl or 0) for p, _, _ in rows
        if p.is_paper_trade and not p.is_open
    )

    return {
        "open":           open_positions,
        "closed":         closed_positions,
        "paper_realized_pnl": round(paper_realized, 2),
        "total_positions": len(rows),
    }


@router.post("/portfolio/{position_id}/close")
def close_position(
    position_id: int,
    body: CloseRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pos = db.query(Portfolio).filter(
        Portfolio.id == position_id,
        Portfolio.user_id == current_user.id,
    ).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    if not pos.is_open:
        raise HTTPException(status_code=400, detail="Position already closed")

    pnl_dollar = pos.shares * (body.exit_price - pos.entry_price)
    pnl_pct    = (body.exit_price - pos.entry_price) / pos.entry_price * 100

    pos.is_open         = False
    pos.exit_price      = body.exit_price
    pos.exit_date       = datetime.utcnow()
    pos.realized_pnl    = round(pnl_dollar, 2)
    pos.realized_pnl_pct= round(pnl_pct, 2)
    db.commit()

    stock = db.query(Stock).filter(Stock.id == pos.stock_id).first()
    return {
        "message": f"Position closed: {stock.ticker if stock else '?'} @ ${body.exit_price:.2f} ({pnl_pct:+.2f}%)",
        "pnl_dollar": round(pnl_dollar, 2),
        "pnl_pct":    round(pnl_pct, 2),
    }


@router.delete("/portfolio/{position_id}", status_code=204)
def delete_position(
    position_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pos = db.query(Portfolio).filter(
        Portfolio.id == position_id,
        Portfolio.user_id == current_user.id,
    ).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found")
    db.delete(pos)
    db.commit()
