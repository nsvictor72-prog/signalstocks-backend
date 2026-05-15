from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import auth, signals, options, performance, email_digest, track_record, portfolio

app = FastAPI(title="SignalStocks API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://signalstocks.io",
        "https://www.signalstocks.io",
        "https://frontend-ten-lilac-39.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",  tags=["auth"])
app.include_router(signals.router,      prefix="/api",       tags=["signals"])
app.include_router(options.router,      prefix="/api",       tags=["options"])
app.include_router(performance.router,  prefix="/api",       tags=["performance"])
app.include_router(email_digest.router,  prefix="/api/email", tags=["email"])
app.include_router(track_record.router, prefix="/api",       tags=["track-record"])
app.include_router(portfolio.router,   prefix="/api",       tags=["portfolio"])


@app.get("/")
def health():
    return {"status": "ok", "service": "signalstocks-api"}
import run_migrations
