import resend
import os

resend.api_key = os.getenv("RESEND_API_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
FROM_EMAIL = os.getenv("FROM_EMAIL", "SignalStocks <noreply@signalstocks.io>")

_BASE_STYLE = """
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  max-width: 480px;
  margin: 0 auto;
  padding: 32px 24px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 12px;
"""

_BTN_STYLE = (
    "display: inline-block; background: #10b981; color: #0f172a; "
    "font-weight: 700; padding: 13px 28px; border-radius: 8px; "
    "text-decoration: none; font-size: 15px;"
)


def send_verification_email(to_email: str, token: str) -> None:
    link = f"{FRONTEND_URL}/verify/{token}"
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": "Verify your SignalStocks account",
        "html": f"""
<div style="{_BASE_STYLE}">
  <h2 style="color: #10b981; margin: 0 0 8px;">Verify your email</h2>
  <p style="color: #94a3b8; margin: 0 0 28px; line-height: 1.6;">
    Thanks for signing up! Click the button below to activate your account.
    This link expires in <strong style="color: #e2e8f0;">24 hours</strong>.
  </p>
  <a href="{link}" style="{_BTN_STYLE}">Verify Email</a>
  <p style="color: #475569; font-size: 12px; margin: 28px 0 0; line-height: 1.5;">
    If you didn't create a SignalStocks account, you can safely ignore this email.
  </p>
</div>
""",
    })


def send_reset_email(to_email: str, token: str) -> None:
    link = f"{FRONTEND_URL}/reset-password/{token}"
    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": "Reset your SignalStocks password",
        "html": f"""
<div style="{_BASE_STYLE}">
  <h2 style="color: #10b981; margin: 0 0 8px;">Reset your password</h2>
  <p style="color: #94a3b8; margin: 0 0 28px; line-height: 1.6;">
    We received a request to reset your password. Click the button below to set a new one.
    This link expires in <strong style="color: #e2e8f0;">1 hour</strong>.
  </p>
  <a href="{link}" style="{_BTN_STYLE}">Reset Password</a>
  <p style="color: #475569; font-size: 12px; margin: 28px 0 0; line-height: 1.5;">
    If you didn't request a password reset, you can safely ignore this email.
    Your password won't change.
  </p>
</div>
""",
    })
