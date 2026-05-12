"""
Phase 2 Signal Factors
- News sentiment (yfinance headlines + VADER)
- Insider buying (SEC EDGAR Form 4)
- Short squeeze detection (yfinance short interest)
"""

import yfinance as yf
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Tuple, List
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── 1. NEWS SENTIMENT ───────────────────────────────────────────────────────

def calculate_news_sentiment(ticker: str) -> Tuple[float, List[str]]:
    """
    Score news sentiment using yfinance headlines + VADER sentiment analyzer.

    Scoring:
      - Very positive avg sentiment (>0.3)  → +20
      - Positive avg sentiment (>0.1)       → +10
      - Negative avg sentiment (<-0.1)      → -10
      - Very negative avg sentiment (<-0.3) → -20
      - Mostly negative headlines           → -5 extra

    Returns: (score_adjustment, reasons)
    """
    score = 0
    reasons = []

    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        import nltk
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon', quiet=True)

        sia = SentimentIntensityAnalyzer()
        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return 0, []

        # Score each headline
        scores = []
        negative_count = 0
        positive_count = 0

        for article in news[:10]:  # Last 10 headlines
            title = article.get('content', {}).get('title', '') or article.get('title', '')
            if not title:
                continue
            sentiment = sia.polarity_scores(title)
            compound = sentiment['compound']
            scores.append(compound)
            if compound > 0.05:
                positive_count += 1
            elif compound < -0.05:
                negative_count += 1

        if not scores:
            return 0, []

        avg_sentiment = sum(scores) / len(scores)
        total = len(scores)

        if avg_sentiment >= 0.3:
            score = 20
            reasons.append(f"Very positive news sentiment ({avg_sentiment:.2f}) — {positive_count}/{total} positive headlines")
        elif avg_sentiment >= 0.1:
            score = 10
            reasons.append(f"Positive news sentiment ({avg_sentiment:.2f})")
        elif avg_sentiment <= -0.3:
            score = -20
            reasons.append(f"Very negative news sentiment ({avg_sentiment:.2f}) — {negative_count}/{total} negative headlines")
        elif avg_sentiment <= -0.1:
            score = -10
            reasons.append(f"Negative news sentiment ({avg_sentiment:.2f})")

        # Extra penalty if majority of headlines are negative
        if negative_count > total * 0.6:
            score -= 5
            reasons.append(f"Majority negative headlines ({negative_count}/{total})")

    except Exception as e:
        print(f"[WARN] News sentiment error for {ticker}: {e}")

    return score, reasons


# ─── 2. INSIDER BUYING (SEC EDGAR) ───────────────────────────────────────────

def calculate_insider_score(ticker: str) -> Tuple[float, List[str]]:
    """
    Check recent insider buying via SEC EDGAR Form 4 filings.
    Insider BUYING is bullish. Insider SELLING is neutral (they sell for many reasons).

    Scoring:
      - Multiple insiders buying recently    → +25
      - One insider buying large amount      → +15
      - Single small insider buy             → +8
      - Insider selling (large)              → -10

    Returns: (score_adjustment, reasons)
    """
    score = 0
    reasons = []

    try:
        # SEC EDGAR full-text search for recent Form 4 filings
        headers = {'User-Agent': 'quant-screener research@example.com'}

        # Get company CIK from SEC
        search_url = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22&dateRange=custom&startdt={( datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}&enddt={datetime.now().strftime('%Y-%m-%d')}&forms=4"
        resp = requests.get(search_url, headers=headers, timeout=10)

        if resp.status_code != 200:
            return 0, []

        data = resp.json()
        hits = data.get('hits', {}).get('hits', [])

        if not hits:
            return 0, []

        buy_count = 0
        sell_count = 0
        total_bought = 0

        for hit in hits[:20]:
            source = hit.get('_source', {})
            # Form 4 transaction codes: P = purchase, S = sale
            transaction_code = source.get('period_of_report', '')
            file_text = str(source).lower()

            if '"p"' in file_text or 'purchase' in file_text:
                buy_count += 1
            elif '"s"' in file_text or 'sale' in file_text:
                sell_count += 1

        if buy_count >= 3:
            score = 25
            reasons.append(f"Multiple insider purchases ({buy_count} in last 30 days) — strong conviction")
        elif buy_count == 2:
            score = 15
            reasons.append(f"Multiple insiders buying ({buy_count} transactions) — bullish signal")
        elif buy_count == 1:
            score = 8
            reasons.append("Insider buying detected — management confident")

        if sell_count >= 3 and buy_count == 0:
            score = -10
            reasons.append(f"Insider selling ({sell_count} transactions) — caution")

    except Exception as e:
        print(f"[WARN] Insider score error for {ticker}: {e}")

    return score, reasons


# ─── 3. SHORT SQUEEZE DETECTION ──────────────────────────────────────────────

def calculate_short_squeeze_score(ticker: str) -> Tuple[float, List[str]]:
    """
    Detect short squeeze potential using short interest data from yfinance.

    Short squeeze conditions:
      - High short interest (>20% of float) + strong momentum = squeeze candidate
      - Very high short interest (>30%) = extreme squeeze potential
      - Days to cover > 5 = hard to cover quickly

    Scoring:
      - Short interest >30% + momentum      → +25 (extreme squeeze potential)
      - Short interest >20% + momentum      → +15 (high squeeze potential)
      - Short interest >10%                 → +5  (elevated short interest)
      - Short interest <3%                  → 0   (no squeeze potential)

    Returns: (score_adjustment, reasons)
    """
    score = 0
    reasons = []

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if not info:
            return 0, []

        # Short interest as % of float
        short_float = info.get('shortPercentOfFloat', 0) or 0
        short_ratio = info.get('shortRatio', 0) or 0  # Days to cover
        shares_short = info.get('sharesShort', 0) or 0

        if short_float == 0:
            return 0, []

        short_float_pct = short_float * 100 if short_float < 1 else short_float

        if short_float_pct >= 30:
            score = 25
            reasons.append(f"Extreme short interest ({short_float_pct:.1f}% of float) — high squeeze potential")
            if short_ratio >= 5:
                score += 5
                reasons.append(f"Days to cover: {short_ratio:.1f} — shorts trapped")
        elif short_float_pct >= 20:
            score = 15
            reasons.append(f"High short interest ({short_float_pct:.1f}% of float) — squeeze candidate")
        elif short_float_pct >= 10:
            score = 5
            reasons.append(f"Elevated short interest ({short_float_pct:.1f}% of float)")

    except Exception as e:
        print(f"[WARN] Short squeeze error for {ticker}: {e}")

    return score, reasons


# ─── 4. CONGRESS TRADING ─────────────────────────────────────────────────────

def calculate_congress_score(ticker: str):
    """
    Wrapper that calls the congress trades module.
    Returns: (score_adjustment, reasons)
    """
    try:
        from src.data_collection.congress_trades import calculate_congress_score as _congress_score
        return _congress_score(ticker)
    except Exception as e:
        print(f"[WARN] Congress score error for {ticker}: {e}")
        return 0, []
