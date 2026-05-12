"""
Extended Hours Price Module
Fetches after-hours and pre-market prices via Yahoo Finance (free, ~15-min delayed).
Validates swing trade signals against overnight price movement.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, time
import pytz

ET = pytz.timezone("America/New_York")

# Gap thresholds
GAP_CANCEL_THRESHOLD = 0.05   # >5%  gap → cancel signal entirely
GAP_WARN_THRESHOLD   = 0.02   # >2%  gap → adjust entry price
# <0.5% gap → signal valid, no change needed


def get_market_session() -> str:
    """Return current market session name based on ET time."""
    now = datetime.now(ET).time()
    if time(4, 0) <= now < time(9, 30):
        return "pre_market"
    elif time(9, 30) <= now <= time(16, 0):
        return "market"
    elif time(16, 0) < now <= time(20, 0):
        return "after_hours"
    else:
        return "closed"


def fetch_extended_price(ticker: str) -> dict:
    """
    Fetch latest extended-hours or pre-market price for a ticker.
    Falls back to regular close if no extended data available.
    """
    result = {
        "ticker":        ticker,
        "regular_close": None,
        "extended_price": None,
        "extended_time":  None,
        "gap_pct":        0.0,
        "session":        get_market_session(),
        "source":         "close",
        "error":          None,
    }
    try:
        stock = yf.Ticker(ticker)

        # Official daily close
        hist = stock.history(period="2d", interval="1d", prepost=False)
        if hist.empty:
            result["error"] = "No price data"
            return result
        result["regular_close"] = float(hist["Close"].iloc[-1])

        # 1-minute bars including pre/post market
        ext = stock.history(period="1d", interval="1m", prepost=True)
        if ext.empty:
            result["extended_price"] = result["regular_close"]
            return result

        last_row = ext.iloc[-1]
        ext_price = float(last_row["Close"])

        result["extended_price"] = ext_price
        result["extended_time"]  = last_row.name  # pandas Timestamp
        result["source"]         = "extended"
        result["gap_pct"]        = (ext_price - result["regular_close"]) / result["regular_close"]

    except Exception as e:
        result["error"]          = str(e)
        result["extended_price"] = result["regular_close"]

    return result


def classify_gap(gap_pct: float) -> dict:
    """Return action label, emoji and color for a given gap percentage."""
    abs_gap   = abs(gap_pct)
    direction = "▲" if gap_pct >= 0 else "▼"
    formatted = f"{direction} {gap_pct:+.2%}"

    if abs_gap >= GAP_CANCEL_THRESHOLD:
        return {"action": "CANCEL", "label": formatted, "emoji": "❌", "color": "red"}
    elif abs_gap >= GAP_WARN_THRESHOLD:
        return {"action": "ADJUST", "label": formatted, "emoji": "⚠️", "color": "orange"}
    else:
        return {"action": "VALID",  "label": formatted, "emoji": "✅", "color": "green"}


def build_orders_table(signals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich active BUY signals with extended-hours pricing.
    Returns a DataFrame ready for the dashboard.
    """
    buy_signals = signals_df[signals_df["signal_type"].str.contains("BUY")].copy()
    if buy_signals.empty:
        return pd.DataFrame()

    rows = []
    for _, sig in buy_signals.iterrows():
        ticker   = sig["ticker"]
        ext      = fetch_extended_price(ticker)
        close    = ext["regular_close"]  or sig["entry_price"]
        ext_px   = ext["extended_price"] or close
        gap_pct  = ext["gap_pct"]
        gap_info = classify_gap(gap_pct)

        # Decide suggested entry
        if gap_info["action"] == "CANCEL":
            suggested_entry = None
        elif gap_info["action"] == "ADJUST":
            suggested_entry = round(ext_px * 1.002, 2)  # tiny buffer above ext price
        else:
            suggested_entry = sig["entry_price"]

        time_str = (ext["extended_time"].strftime("%I:%M %p ET")
                    if ext["extended_time"] is not None else "N/A")

        rows.append({
            "Ticker":           ticker,
            "Close":            close,
            "Extended Price":   ext_px,
            "Gap %":            gap_pct,
            "_action":          gap_info["action"],
            "_emoji":           gap_info["emoji"],
            "_gap_label":       gap_info["label"],
            "Score":            sig["composite_score"],
            "Confidence":       sig["confidence"],
            "Suggested Entry":  suggested_entry,
            "Stop Loss":        sig["stop_loss"],
            "Take Profit":      sig["take_profit_1"],
            "Reason":           sig.get("primary_reason", ""),
            "Last Updated":     time_str,
        })

    return pd.DataFrame(rows)
