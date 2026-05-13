"""
Daily signal generation for the S&P 500 universe.
Run: python generate_sp500_signals.py

Steps:
  1. Query all active tickers from the database.
  2. Run the multi-factor signal generator for each ticker.
  3. Call Claude AI to add a "Why This Trade" explanation to every new signal
     (signals that already have an explanation are skipped).

Environment variables required:
  DATABASE_URL        — PostgreSQL connection string (or SQLite fallback)
  ANTHROPIC_API_KEY   — Anthropic API key for Claude explanations
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from database import get_session, Stock
from signals.signal_generator import SignalGenerator
from signals.explain_signals import add_explanations_to_db


def main() -> None:
    session = get_session()

    # ── 1. Fetch universe ────────────────────────────────────────────────────
    tickers = [s.ticker for s in session.query(Stock).filter_by(is_active=True).all()]
    print(f"[INFO] {len(tickers)} active tickers in universe")

    if not tickers:
        print("[WARN] No active tickers found — exiting.")
        return

    # ── 2. Generate signals ──────────────────────────────────────────────────
    generator = SignalGenerator(session=session)
    generator.generate_signals_for_universe(tickers)

    # ── 3. Add Claude explanations (skips signals that already have one) ─────
    if os.environ.get("ANTHROPIC_API_KEY"):
        add_explanations_to_db(session, limit=200)
    else:
        print("[SKIP] ANTHROPIC_API_KEY not set — skipping AI explanations.")

    session.close()
    print("\n[DONE] generate_sp500_signals.py complete.")


if __name__ == "__main__":
    main()
