from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import Signal, Stock
from routers.auth import get_current_user, get_db

router = APIRouter()

FREE_LIMIT = 10
PREMIUM_LIMIT = 15


@router.get("/signals")
def get_signals(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    limit = PREMIUM_LIMIT if current_user.tier == "premium" else FREE_LIMIT

    rows = (
        db.query(Signal, Stock.ticker, Stock.company_name, Stock.sector)
        .join(Stock, Signal.stock_id == Stock.id)
        .filter(Signal.is_active == True)
        .order_by(Signal.composite_score.desc())
        .limit(limit)
        .all()
    )

    signals = []
    for sig, ticker, company, sector in rows:
        signals.append({
            "ticker": ticker,
            "company_name": company,
            "sector": sector,
            "signal_type": sig.signal_type,
            "signal_strength": sig.signal_strength,
            "composite_score": sig.composite_score,
            "technical_score": sig.technical_score,
            "fundamental_score": sig.fundamental_score,
            "momentum_score": sig.momentum_score,
            "confidence": sig.confidence,
            "entry_price": sig.entry_price,
            "stop_loss": sig.stop_loss,
            "take_profit_1": sig.take_profit_1,
            "take_profit_2": sig.take_profit_2,
            "primary_reason": sig.primary_reason,
            "contributing_factors": sig.contributing_factors,
            "explanation": sig.explanation,
            "signal_date": sig.signal_date.isoformat() if sig.signal_date else None,
        })

    return {"signals": signals, "count": len(signals), "tier": current_user.tier}
