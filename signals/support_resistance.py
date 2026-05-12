"""
Support & Resistance Level Detection
Calculates key price levels from historical data using:
- Swing highs/lows (pivot points)
- Volume-weighted price clusters
- Round number levels
"""

import numpy as np
from typing import Tuple, List, Dict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_session, Stock, PriceData


def find_pivot_points(prices: list, window: int = 5) -> Tuple[List[float], List[float]]:
    """
    Find swing highs (resistance) and swing lows (support)
    using a rolling window approach.
    
    A pivot high = highest point in window on both sides
    A pivot low  = lowest point in window on both sides
    """
    highs     = [p.high  for p in prices]
    lows      = [p.low   for p in prices]
    closes    = [p.close for p in prices]
    volumes   = [p.volume or 1 for p in prices]

    pivot_highs = []
    pivot_lows  = []

    for i in range(window, len(prices) - window):
        # Pivot high — local maximum
        if highs[i] == max(highs[i-window:i+window+1]):
            pivot_highs.append((highs[i], volumes[i]))

        # Pivot low — local minimum
        if lows[i] == min(lows[i-window:i+window+1]):
            pivot_lows.append((lows[i], volumes[i]))

    return pivot_highs, pivot_lows


def cluster_levels(levels: List[Tuple[float, float]], tolerance_pct: float = 0.015) -> List[Dict]:
    """
    Cluster nearby price levels together.
    Two levels are the same if within tolerance_pct of each other.
    Returns clusters sorted by strength (number of touches × volume).
    """
    if not levels:
        return []

    clusters = []
    used = set()

    for i, (price, vol) in enumerate(levels):
        if i in used:
            continue

        cluster_prices = [price]
        cluster_vols   = [vol]

        for j, (price2, vol2) in enumerate(levels):
            if j == i or j in used:
                continue
            if abs(price - price2) / price <= tolerance_pct:
                cluster_prices.append(price2)
                cluster_vols.append(vol2)
                used.add(j)

        used.add(i)
        avg_price  = np.mean(cluster_prices)
        total_vol  = sum(cluster_vols)
        touches    = len(cluster_prices)

        clusters.append({
            'price':   round(avg_price, 2),
            'touches': touches,
            'volume':  total_vol,
            'strength': touches * (total_vol / 1e6),  # normalize volume
        })

    return sorted(clusters, key=lambda x: x['strength'], reverse=True)


def get_support_resistance(ticker: str, session=None, lookback_days: int = 180):
    """
    Calculate support and resistance levels for a ticker.
    
    Returns dict with:
      - current_price
      - supports:    list of support levels below current price
      - resistances: list of resistance levels above current price
      - nearest_support:    closest support below
      - nearest_resistance: closest resistance above
      - risk_reward:        ratio of upside to downside
    """
    result = {
        'ticker':             ticker,
        'current_price':      None,
        'supports':           [],
        'resistances':        [],
        'nearest_support':    None,
        'nearest_resistance': None,
        'support_distance_pct':    None,
        'resistance_distance_pct': None,
        'risk_reward':        None,
        'error':              None,
    }

    try:
        if session is None:
            session = get_session()

        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock:
            result['error'] = 'Stock not found'
            return result

        prices = session.query(PriceData).filter_by(
            stock_id=stock.id
        ).order_by(PriceData.date.desc()).limit(lookback_days).all()

        if len(prices) < 30:
            result['error'] = 'Insufficient price history'
            return result

        # Reverse to chronological order
        prices = list(reversed(prices))

        current_price = prices[-1].close
        result['current_price'] = current_price

        # Find pivot points
        pivot_highs, pivot_lows = find_pivot_points(prices, window=5)

        # Cluster into levels
        resistance_clusters = cluster_levels(pivot_highs)
        support_clusters    = cluster_levels(pivot_lows)

        # Filter: supports below current, resistances above
        supports    = [c for c in support_clusters    if c['price'] < current_price * 0.995]
        resistances = [c for c in resistance_clusters if c['price'] > current_price * 1.005]

        # Sort supports descending (nearest first), resistances ascending
        supports    = sorted(supports,    key=lambda x: x['price'], reverse=True)[:5]
        resistances = sorted(resistances, key=lambda x: x['price'])[:5]

        result['supports']    = supports
        result['resistances'] = resistances

        # Nearest levels
        if supports:
            nearest_sup = supports[0]['price']
            result['nearest_support']           = nearest_sup
            result['support_distance_pct']      = (current_price - nearest_sup) / current_price * 100

        if resistances:
            nearest_res = resistances[0]['price']
            result['nearest_resistance']        = nearest_res
            result['resistance_distance_pct']   = (nearest_res - current_price) / current_price * 100

        # Risk/reward ratio
        if result['nearest_support'] and result['nearest_resistance']:
            upside   = result['nearest_resistance'] - current_price
            downside = current_price - result['nearest_support']
            if downside > 0:
                result['risk_reward'] = round(upside / downside, 2)

    except Exception as e:
        result['error'] = str(e)

    return result


def calculate_sr_score(ticker: str, session=None) -> Tuple[float, List[str]]:
    """
    Score a stock based on its position relative to support/resistance.

    Scoring:
      - Price near strong support (<3% above)    → +20 (great entry)
      - Price near support (<5% above)            → +12
      - Risk/reward > 3:1                         → +15
      - Risk/reward > 2:1                         → +8
      - Price near resistance (<3% below)         → -15 (bad entry)
      - Price near resistance (<5% below)         → -8
      - Support just broken (price below support) → -10

    Returns: (score_adjustment, reasons)
    """
    score   = 0
    reasons = []

    try:
        sr = get_support_resistance(ticker, session)

        if sr.get('error') or not sr['current_price']:
            return 0, []

        sup_dist = sr.get('support_distance_pct')
        res_dist = sr.get('resistance_distance_pct')
        rr       = sr.get('risk_reward')
        sup      = sr.get('nearest_support')
        res      = sr.get('nearest_resistance')
        price    = sr['current_price']

        # Support proximity scoring
        if sup_dist is not None:
            if sup_dist <= 3.0:
                score += 20
                reasons.append(f"Near strong support at ${sup:.2f} ({sup_dist:.1f}% below) — ideal entry")
            elif sup_dist <= 5.0:
                score += 12
                reasons.append(f"Support at ${sup:.2f} ({sup_dist:.1f}% below)")

        # Resistance proximity scoring
        if res_dist is not None:
            if res_dist <= 3.0:
                score -= 15
                reasons.append(f"Near resistance at ${res:.2f} ({res_dist:.1f}% above) — avoid entry")
            elif res_dist <= 5.0:
                score -= 8
                reasons.append(f"Approaching resistance at ${res:.2f} ({res_dist:.1f}% above)")

        # Risk/reward scoring
        if rr is not None:
            if rr >= 3.0:
                score += 15
                reasons.append(f"Excellent risk/reward ratio ({rr:.1f}:1) — strong setup")
            elif rr >= 2.0:
                score += 8
                reasons.append(f"Good risk/reward ratio ({rr:.1f}:1)")
            elif rr < 1.0:
                score -= 5
                reasons.append(f"Poor risk/reward ({rr:.1f}:1) — resistance too close")

    except Exception as e:
        print(f"[WARN] S/R score error for {ticker}: {e}")

    return score, reasons
