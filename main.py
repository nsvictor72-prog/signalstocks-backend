from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers import auth, signals, options, performance, email_digest

app = FastAPI(title="SignalStocks API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",  tags=["auth"])
app.include_router(signals.router,      prefix="/api",       tags=["signals"])
app.include_router(options.router,      prefix="/api",       tags=["options"])
app.include_router(performance.router,  prefix="/api",       tags=["performance"])
app.include_router(email_digest.router, prefix="/api/email", tags=["email"])


@app.get("/")
def health():
    return {"status": "ok", "service": "signalstocks-api"}
