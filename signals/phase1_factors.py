"""
Phase 1 Signal Factors
- Volume spike detection
- Earnings calendar awareness
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, List
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_session, Stock, PriceData


def calculate_volume_score(ticker: str, session=None) -> Tuple[float, List[str]]:
    """
    Calculate volume score (0-100) based on volume spikes vs average.
    
    Scoring:
      - Volume > 3x average  → +25 (very strong confirmation)
      - Volume > 2x average  → +15 (strong confirmation)
      - Volume > 1.5x average → +8 (moderate confirmation)
      - Volume < 0.5x average → -10 (weak, no conviction)
    
    Returns: (score_adjustment, reasons)
    """
    reasons = []
    score = 0

    try:
        if session is None:
            session = get_session()

        stock = session.query(Stock).filter_by(ticker=ticker).first()
        if not stock:
            return 0, []

        # Get last 30 days of volume from DB
        prices = session.query(PriceData).filter_by(
            stock_id=stock.id
        ).order_by(PriceData.date.desc()).limit(30).all()

        if len(prices) < 10:
            return 0, ["Insufficient volume history"]

        # Average volume over last 20 days (exclude today)
        volumes = [p.volume for p in prices[1:21] if p.volume and p.volume > 0]
        if not volumes:
            return 0, []

        avg_volume = sum(volumes) / len(volumes)
        today_volume = prices[0].volume

        if not today_volume or avg_volume == 0:
            return 0, []

        ratio = today_volume / avg_volume

        if ratio >= 3.0:
            score = 25
            reasons.append(f"Extreme volume spike ({ratio:.1f}x average) — strong conviction")
        elif ratio >= 2.0:
            score = 15
            reasons.append(f"High volume spike ({ratio:.1f}x average) — confirms move")
        elif ratio >= 1.5:
            score = 8
            reasons.append(f"Above average volume ({ratio:.1f}x) — moderate conviction")
        elif ratio < 0.5:
            score = -10
            reasons.append(f"Very low volume ({ratio:.1f}x average) — weak conviction")

    except Exception as e:
        print(f"[WARN] Volume score error for {ticker}: {e}")

    return score, reasons


def calculate_earnings_risk(ticker: str) -> Tuple[float, List[str]]:
    """
    Check if earnings are coming up soon and adjust signal accordingly.
    
    Rules:
      - Earnings in 1-2 days  → -30 (very high risk, avoid entering)
      - Earnings in 3-5 days  → -15 (elevated risk, caution)
      - Earnings in 6-14 days → -5  (mild risk, be aware)
      - No earnings soon      →  0  (no adjustment)
      - Earnings just passed (1-3 days ago) → +10 (uncertainty resolved)
    
    Returns: (score_adjustment, reasons)
    """
    reasons = []
    score = 0

    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar

        if calendar is None:
            return 0, []

        # Handle both dict and DataFrame formats (yfinance changed in newer versions)
        if isinstance(calendar, dict):
            earnings_date = calendar.get('Earnings Date', [None])
            if isinstance(earnings_date, list):
                earnings_date = earnings_date[0] if earnings_date else None
            if earnings_date is None:
                return 0, []
        elif hasattr(calendar, 'empty'):
            if calendar.empty:
                return 0, []
            if 'Earnings Date' in calendar.index:
                earnings_date = calendar.loc['Earnings Date'].iloc[0]
            elif 'Earnings Date' in calendar.columns:
                earnings_date = pd.to_datetime(calendar['Earnings Date'].iloc[0])
            else:
                return 0, []
        else:
            return 0, []

        if pd.isna(earnings_date):
            return 0, []

        earnings_date = pd.to_datetime(earnings_date).tz_localize(None)
        today = pd.Timestamp.now().normalize()
        days_until = (earnings_date - today).days

        if days_until < 0 and days_until >= -3:
            score = 10
            reasons.append(f"Earnings just reported ({abs(days_until)}d ago) — uncertainty resolved")
        elif 0 <= days_until <= 2:
            score = -30
            reasons.append(f"⚠️ Earnings in {days_until+1} day(s) — very high risk, avoid entering")
        elif days_until <= 5:
            score = -15
            reasons.append(f"Earnings in {days_until} days — elevated risk")
        elif days_until <= 14:
            score = -5
            reasons.append(f"Earnings in {days_until} days — be aware")

    except Exception as e:
        print(f"[WARN] Earnings check error for {ticker}: {e}")

    return score, reasons
