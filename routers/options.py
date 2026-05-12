from fastapi import APIRouter, Depends
from datetime import date
import os
import yfinance as yf

from routers.auth import get_current_user

router = APIRouter()

OPTIONS_TICKERS = os.getenv("OPTIONS_TICKERS", "AAPL,NVDA,TSLA,SPY,QQQ,AMD,META").split(",")


def _unusual_contracts(df, current_price: float, option_type: str) -> list:
    if df is None or df.empty or current_price is None or current_price <= 0:
        return []
    near = df[abs(df["strike"] - current_price) / current_price < 0.05].copy()
    near = near[near["volume"].fillna(0) > 0]
    near["vol_oi_ratio"] = near["volume"] / near["openInterest"].replace(0, 1)
    near = near.sort_values("vol_oi_ratio", ascending=False).head(3)
    records = []
    for _, row in near.iterrows():
        records.append({
            "type": option_type,
            "strike": row["strike"],
            "last_price": row["lastPrice"],
            "volume": int(row["volume"]),
            "open_interest": int(row["openInterest"]),
            "vol_oi_ratio": round(float(row["vol_oi_ratio"]), 2),
            "implied_volatility": round(float(row["impliedVolatility"]), 4) if row["impliedVolatility"] else None,
        })
    return records


@router.get("/options")
def get_options(current_user=Depends(get_current_user)):
    results = []
    for ticker in OPTIONS_TICKERS:
        try:
            yf_ticker = yf.Ticker(ticker)
            expirations = yf_ticker.options
            if not expirations:
                results.append({"ticker": ticker, "error": "No options data"})
                continue

            exp = expirations[0]
            chain = yf_ticker.option_chain(exp)
            info = yf_ticker.fast_info
            current_price = getattr(info, "last_price", None) or getattr(info, "previous_close", None)

            unusual_calls = _unusual_contracts(chain.calls, current_price, "call")
            unusual_puts  = _unusual_contracts(chain.puts, current_price, "put")

            results.append({
                "ticker": ticker,
                "current_price": current_price,
                "expiration": exp,
                "unusual_calls": unusual_calls,
                "unusual_puts": unusual_puts,
            })
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})

    return {"options": results, "as_of": date.today().isoformat()}
