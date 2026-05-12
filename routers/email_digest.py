from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

from database import Signal, Stock
from routers.auth import require_premium, get_db

router = APIRouter()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "signals@signalstocks.io")


class DigestRequest(BaseModel):
    to_email: str


def _build_html(rows: list) -> str:
    row_html = ""
    for sig, ticker, company in rows:
        color = "#22c55e" if "BUY" in sig.signal_type else "#ef4444" if sig.signal_type == "SELL" else "#64748b"
        entry = f"${sig.entry_price:.2f}" if sig.entry_price else "—"
        row_html += f"""
        <tr>
          <td style="padding:8px;font-weight:bold">{ticker}</td>
          <td style="padding:8px">{company or ''}</td>
          <td style="padding:8px">
            <span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:12px">{sig.signal_type}</span>
          </td>
          <td style="padding:8px">{sig.composite_score:.0f}</td>
          <td style="padding:8px">{entry}</td>
          <td style="padding:8px;font-size:11px;color:#64748b">{sig.primary_reason or ''}</td>
        </tr>"""

    return f"""<html><body style="font-family:sans-serif;max-width:700px;margin:auto">
      <h2 style="color:#1e293b">SignalStocks Daily Digest</h2>
      <p style="color:#64748b">Top signals as of today</p>
      <table width="100%" border="0" cellspacing="0" style="border-collapse:collapse">
        <thead>
          <tr style="background:#f1f5f9">
            <th style="padding:8px;text-align:left">Ticker</th>
            <th style="padding:8px;text-align:left">Company</th>
            <th style="padding:8px;text-align:left">Signal</th>
            <th style="padding:8px;text-align:left">Score</th>
            <th style="padding:8px;text-align:left">Entry</th>
            <th style="padding:8px;text-align:left">Reason</th>
          </tr>
        </thead>
        <tbody>{row_html}</tbody>
      </table>
      <p style="color:#94a3b8;font-size:12px;margin-top:24px">SignalStocks &bull; signalstocks.io</p>
    </body></html>"""


@router.post("/send-digest")
def send_digest(
    body: DigestRequest,
    current_user=Depends(require_premium),
    db: Session = Depends(get_db),
):
    if not SENDGRID_API_KEY:
        raise HTTPException(status_code=500, detail="SENDGRID_API_KEY not configured")

    rows = (
        db.query(Signal, Stock.ticker, Stock.company_name)
        .join(Stock, Signal.stock_id == Stock.id)
        .filter(Signal.is_active == True)
        .order_by(Signal.composite_score.desc())
        .limit(10)
        .all()
    )

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=body.to_email,
        subject="SignalStocks Daily Signal Digest",
        html_content=_build_html(rows),
    )

    try:
        SendGridAPIClient(SENDGRID_API_KEY).send(message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SendGrid error: {e}")

    return {"status": "sent", "to": body.to_email, "signals_included": len(rows)}
