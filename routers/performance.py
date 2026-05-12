from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import Signal, Stock
from routers.auth import get_current_user, get_db

router = APIRouter()


@router.get("/performance")
def get_performance(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    closed = (
        db.query(Signal)
        .filter(Signal.is_active == False, Signal.pnl_pct != None)
        .all()
    )

    if not closed:
        return {"message": "No closed trades yet", "total_trades": 0}

    pnls = [s.pnl_pct for s in closed]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    recent = sorted(closed, key=lambda s: s.signal_date or 0, reverse=True)[:50]
    stock_map = {
        s.stock_id: db.query(Stock).filter(Stock.id == s.stock_id).first()
        for s in recent
    }

    trades = []
    for s in recent:
        stock = stock_map.get(s.stock_id)
        trades.append({
            "ticker": stock.ticker if stock else "?",
            "signal_type": s.signal_type,
            "entry_price": s.entry_price,
            "exit_price": s.exit_price,
            "pnl_pct": s.pnl_pct,
            "exit_reason": s.exit_reason,
            "signal_date": s.signal_date.isoformat() if s.signal_date else None,
            "exit_date": s.exit_date.isoformat() if s.exit_date else None,
        })

    return {
        "summary": {
            "total_trades": len(pnls),
            "win_rate_pct": round(len(wins) / len(pnls) * 100, 1),
            "avg_return_pct": round(sum(pnls) / len(pnls), 2),
            "avg_win_pct": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss_pct": round(sum(losses) / len(losses), 2) if losses else 0,
            "best_trade_pct": round(max(pnls), 2),
            "worst_trade_pct": round(min(pnls), 2),
        },
        "recent_trades": trades,
    }
