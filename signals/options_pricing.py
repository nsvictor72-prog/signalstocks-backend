"""
Options pricing utilities — covered call premium estimation.
Uses the same Black-Scholes + historical-vol approach as backtest_sell_premium.py
so signal estimates are consistent with the +198.76% backtest results.
"""
import numpy as np
from scipy.stats import norm

RISK_FREE_RATE = 0.053   # ~5.3% (approx 10-yr Treasury)
IV_SCALING     = 1.15    # Historical vol → implied vol proxy (matches backtest)
MIN_IV         = 0.10    # Floor: even low-vol stocks have some IV
MAX_IV         = 2.00    # Cap: avoids absurd estimates on extremely volatile names
MIN_PREMIUM    = 0.01    # Never return exactly $0


def estimate_iv(close_prices: list) -> float:
    """
    Annualised volatility from closing prices, scaled to approximate IV.
    Matches estimate_iv() in backtest_sell_premium.py exactly.
    Returns a decimal (e.g. 0.35 = 35%).
    """
    if len(close_prices) < 10:
        return 0.30  # conservative fallback for thin history
    closes = np.array([p for p in close_prices if p and p > 0], dtype=float)
    if len(closes) < 10:
        return 0.30
    log_returns = np.diff(np.log(closes))
    hist_vol = float(np.std(log_returns)) * np.sqrt(252)
    iv = hist_vol * IV_SCALING
    return float(np.clip(iv, MIN_IV, MAX_IV))


def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """
    European call price via Black-Scholes.
    S: spot price  K: strike  T: time to expiry (years)
    r: risk-free rate  sigma: annualised volatility
    Matches black_scholes_call() in backtest_sell_premium.py exactly.
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        price = float(S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2))
        return max(price, MIN_PREMIUM)
    except Exception:
        return 0.0


def calculate_cc_premium(
    current_price: float,
    strike: float | None = None,
    days_to_expiry: int = 30,
    iv: float | None = None,
) -> float:
    """
    Estimate the covered call premium per share using Black-Scholes.
    Defaults: 10% OTM strike, 30-DTE, IV from estimate_iv() or 25% fallback.
    Returns dollar amount per share.
    """
    if current_price <= 0:
        return 0.0
    K     = strike if strike else current_price * 1.10
    T     = days_to_expiry / 365.0
    sigma = iv if iv else 0.25
    return black_scholes_call(current_price, K, T, RISK_FREE_RATE, sigma)
