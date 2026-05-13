"""
Claude AI explanation generator for trading signals.
Adds a 2-3 sentence "Why This Trade" explainer to each signal.

Model: claude-sonnet-4-20250514 (user-specified; upgrade to claude-sonnet-4-6 when retiring)
Budget: ~$0.03 per 100 signals at Sonnet pricing.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic
from sqlalchemy.orm import Session

from database import Signal, Stock

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _build_summaries(factors: list[str]) -> tuple[str, str]:
    """Extract sentiment and insider summaries from contributing factors."""
    sentiment_kw = {"sentiment", "news", "bullish", "bearish", "positive", "negative"}
    insider_kw    = {"insider", "short", "squeeze", "institutional", "buying"}

    sentiment = [f for f in factors if any(k in f.lower() for k in sentiment_kw)]
    insider   = [f for f in factors if any(k in f.lower() for k in insider_kw)]

    return (
        ", ".join(sentiment[:2]) if sentiment else "Neutral market sentiment",
        ", ".join(insider[:2])   if insider   else "No unusual insider activity detected",
    )


def generate_explanation(signal_data: dict) -> str | None:
    """
    Call Claude to produce a 2-3 sentence retail-trader explanation.
    Returns None (and prints a warning) if the API call fails.
    """
    ticker    = signal_data.get("ticker", "?")
    sig_type  = signal_data.get("signal_type", "")
    score     = signal_data.get("composite_score", 0)
    conf      = signal_data.get("confidence", 0)
    entry     = signal_data.get("entry_price") or 0
    reason    = signal_data.get("primary_reason") or "Multi-factor analysis"
    factors   = signal_data.get("all_reasons") or signal_data.get("contributing_factors") or []

    sentiment_summary, insider_summary = _build_summaries(factors)

    prompt = (
        f"Given this stock signal, explain why this is a good/bad trade opportunity:\n"
        f"Ticker: {ticker}\n"
        f"Signal: {sig_type}\n"
        f"Score: {score}/100\n"
        f"Confidence: {conf}%\n"
        f"Entry Price: ${float(entry):.2f}\n"
        f"Technical Reason: {reason}\n"
        f"Sentiment: {sentiment_summary}\n"
        f"Insider Activity: {insider_summary}\n\n"
        f"Provide a 2-3 sentence explanation that a retail trader would understand. "
        f"Focus on the key factors driving this signal."
    )

    try:
        client = _get_client()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except anthropic.APIError as e:
        print(f"[WARN] Claude API error for {ticker}: {e}")
        return None
    except Exception as e:
        print(f"[WARN] Unexpected error generating explanation for {ticker}: {e}")
        return None


def add_explanation_to_signal(signal_id: int, session: Session, signal_data: dict) -> bool:
    """
    Generate and persist an explanation for a single signal row.
    Skips if explanation already exists.
    """
    sig = session.get(Signal, signal_id)
    if sig is None:
        return False
    if sig.explanation:
        return True  # already has one

    text = generate_explanation(signal_data)
    if text is None:
        return False

    sig.explanation = text
    session.commit()
    return True


def add_explanations_to_db(session: Session, limit: int = 200) -> int:
    """
    Backfill explanations for active signals that have none.
    Processes up to `limit` signals per run.
    Returns the count of explanations written.
    """
    rows = (
        session.query(Signal, Stock.ticker, Stock.company_name)
        .join(Stock, Signal.stock_id == Stock.id)
        .filter(Signal.is_active == True, Signal.explanation == None)
        .order_by(Signal.composite_score.desc())
        .limit(limit)
        .all()
    )

    if not rows:
        print("[CLAUDE] All active signals already have explanations.")
        return 0

    print(f"[CLAUDE] Generating explanations for {len(rows)} signals...")
    written = 0

    for sig, ticker, company in rows:
        signal_data = {
            "ticker":          ticker,
            "signal_type":     sig.signal_type,
            "composite_score": sig.composite_score,
            "confidence":      sig.confidence,
            "entry_price":     sig.entry_price,
            "primary_reason":  sig.primary_reason,
            "contributing_factors": sig.contributing_factors or [],
        }

        text = generate_explanation(signal_data)
        if text:
            sig.explanation = text
            session.commit()
            written += 1
            print(f"  [OK] {ticker}: {text[:80]}…")
        else:
            print(f"  [SKIP] {ticker}: explanation skipped (API error or missing key)")

    print(f"[CLAUDE] Done — {written}/{len(rows)} explanations written.")
    return written
