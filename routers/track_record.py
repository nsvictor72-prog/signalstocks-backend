"""
GET /api/track-record — public endpoint, no auth required.
Returns aggregated performance from closed signals + monthly breakdown.
Results are cached in-process for 1 hour to avoid recalculating on every hit.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import time

from database import Signal, Stock
from routers.auth import get_db

router = APIRouter()

# ── Simple 1-hour in-process cache ───────────────────────────────────────────
_cache: dict = {}
_cache_ts: dict = {}
_TTL = 3600  # seconds


def _get(key: str):
    if key in _cache and time.time() - _cache_ts.get(key, 0) < _TTL:
        return _cache[key]
    return None


def _set(key: str, value):
    _cache[key] = value
    _cache_ts[key] = time.time()


# ── Helper ────────────────────────────────────────────────────────────────────

def _profit_factor(wins: list[float], losses: list[float]) -> float | None:
    if not losses:
        return None
    loss_sum = abs(sum(losses))
    if loss_sum == 0:
        return None
    return round(sum(wins) / loss_sum, 2)


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/track-record")
def get_track_record(db: Session = Depends(get_db)):
    cached = _get("track_record")
    if cached:
        return cached

    # All closed trades with a pnl recorded
    rows = (
        db.query(Signal, Stock.ticker, Stock.company_name)
        .join(Stock, Signal.stock_id == Stock.id)
        .filter(
            Signal.is_active == False,
            Signal.exit_date.isnot(None),
            Signal.pnl_pct.isnot(None),
        )
        .order_by(Signal.exit_date.desc())
        .all()
    )

    if not rows:
        result = {
            "total_trades": 0,
            "summary": None,
            "ytd": None,
            "monthly": [],
            "recent_trades": [],
        }
        _set("track_record", result)
        return result

    pnls = [sig.pnl_pct for sig, _, _ in rows]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    # ── Monthly breakdown ─────────────────────────────────────────────────────
    monthly_buckets: dict[str, list[float]] = {}
    for sig, _, _ in rows:
        key = sig.exit_date.strftime("%Y-%m")
        monthly_buckets.setdefault(key, []).append(sig.pnl_pct)

    monthly = []
    for key in sorted(monthly_buckets):
        bucket = monthly_buckets[key]
        bucket_wins = [p for p in bucket if p > 0]
        bucket_losses = [p for p in bucket if p <= 0]
        monthly.append({
            "month": key,
            "label": datetime.strptime(key, "%Y-%m").strftime("%b '%y"),
            "avg_pnl": round(sum(bucket) / len(bucket), 2),
            "total_pnl": round(sum(bucket), 2),
            "trades": len(bucket),
            "wins": len(bucket_wins),
            "win_rate": round(len(bucket_wins) / len(bucket) * 100, 1),
        })

    # ── YTD ───────────────────────────────────────────────────────────────────
    ytd_start = datetime(datetime.utcnow().year, 1, 1)
    ytd_rows  = [(s, t, c) for s, t, c in rows if s.exit_date >= ytd_start]
    ytd_pnls  = [s.pnl_pct for s, _, _ in ytd_rows]
    ytd_wins  = [p for p in ytd_pnls if p > 0]
    ytd_losses= [p for p in ytd_pnls if p <= 0]

    ytd = {
        "trades": len(ytd_rows),
        "win_rate_pct": round(len(ytd_wins) / len(ytd_pnls) * 100, 1) if ytd_pnls else 0,
        "avg_pnl_pct":  round(sum(ytd_pnls) / len(ytd_pnls), 2) if ytd_pnls else 0,
        "total_pnl_pct": round(sum(ytd_pnls), 2) if ytd_pnls else 0,
        "profit_factor": _profit_factor(ytd_wins, ytd_losses),
    }

    # ── Summary ───────────────────────────────────────────────────────────────
    summary = {
        "total_trades":    len(pnls),
        "win_rate_pct":    round(len(wins) / len(pnls) * 100, 1),
        "avg_win_pct":     round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss_pct":    round(sum(losses) / len(losses), 2) if losses else 0,
        "profit_factor":   _profit_factor(wins, losses),
        "best_trade_pct":  round(max(pnls), 2),
        "worst_trade_pct": round(min(pnls), 2),
        "total_pnl_pct":   round(sum(pnls), 2),
    }

    # ── Recent 20 trades ──────────────────────────────────────────────────────
    recent_trades = []
    for sig, ticker, company in rows[:20]:
        days = None
        if sig.signal_date and sig.exit_date:
            days = max(0, (sig.exit_date - sig.signal_date).days)
        recent_trades.append({
            "ticker":       ticker,
            "company":      company,
            "signal_type":  sig.signal_type,
            "entry_price":  sig.entry_price,
            "exit_price":   sig.exit_price,
            "pnl_pct":      sig.pnl_pct,
            "exit_reason":  sig.exit_reason,
            "signal_date":  sig.signal_date.isoformat() if sig.signal_date else None,
            "exit_date":    sig.exit_date.isoformat(),
            "days_held":    days,
        })

    result = {
        "total_trades": len(pnls),
        "summary":      summary,
        "ytd":          ytd,
        "monthly":      monthly,
        "recent_trades": recent_trades,
        "as_of":        datetime.utcnow().isoformat(),
    }

    _set("track_record", result)
    return result
