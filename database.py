"""
Database Models for Quantitative Stock Screener
Defines schema for storing stock data, signals, and performance metrics
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Stock(Base):
    """Master table of stocks in the universe"""
    __tablename__ = 'stocks'
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(200))
    sector = Column(String(50))
    industry = Column(String(100))
    market_cap = Column(Float)
    country = Column(String(50), default='US')
    exchange = Column(String(20))
    is_active = Column(Boolean, default=True)
    added_date = Column(DateTime, default=datetime.utcnow)
    
    price_data = relationship("PriceData", back_populates="stock", cascade="all, delete-orphan")
    fundamentals = relationship("Fundamentals", back_populates="stock", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="stock", cascade="all, delete-orphan")


class PriceData(Base):
    """Historical OHLCV data"""
    __tablename__ = 'price_data'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    adj_close = Column(Float)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    sma_200 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr = Column(Float)
    obv = Column(Float)
    
    stock = relationship("Stock", back_populates="price_data")


class Fundamentals(Base):
    """Fundamental data snapshot"""
    __tablename__ = 'fundamentals'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    pe_ratio = Column(Float)
    ps_ratio = Column(Float)
    pb_ratio = Column(Float)
    peg_ratio = Column(Float)
    ev_ebitda = Column(Float)
    revenue_ttm = Column(Float)
    revenue_growth_yoy = Column(Float)
    revenue_growth_qoq = Column(Float)
    earnings_ttm = Column(Float)
    earnings_growth_yoy = Column(Float)
    earnings_growth_qoq = Column(Float)
    eps_ttm = Column(Float)
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_margin = Column(Float)
    roe = Column(Float)
    roa = Column(Float)
    roic = Column(Float)
    total_cash = Column(Float)
    total_debt = Column(Float)
    debt_to_equity = Column(Float)
    current_ratio = Column(Float)
    free_cash_flow = Column(Float)
    fcf_margin = Column(Float)
    beta = Column(Float)
    shares_outstanding = Column(Float)
    float_shares = Column(Float)
    short_interest = Column(Float)
    short_ratio = Column(Float)
    
    stock = relationship("Stock", back_populates="fundamentals")


class NewsArticle(Base):
    """News articles for sentiment analysis"""
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    published_date = Column(DateTime, nullable=False, index=True)
    headline = Column(Text)
    description = Column(Text)
    url = Column(String(500))
    source = Column(String(100))
    sentiment_score = Column(Float)
    sentiment_label = Column(String(20))
    sentiment_confidence = Column(Float)
    keywords = Column(JSON)
    event_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class EarningsEvent(Base):
    """Earnings calendar and results"""
    __tablename__ = 'earnings_events'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    report_date = Column(DateTime, nullable=False, index=True)
    fiscal_quarter = Column(String(10))
    fiscal_year = Column(Integer)
    eps_estimate = Column(Float)
    eps_actual = Column(Float)
    eps_surprise = Column(Float)
    eps_surprise_pct = Column(Float)
    revenue_estimate = Column(Float)
    revenue_actual = Column(Float)
    revenue_surprise = Column(Float)
    revenue_surprise_pct = Column(Float)
    guidance_provided = Column(Boolean)
    guidance_direction = Column(String(20))
    price_change_1d = Column(Float)
    price_change_5d = Column(Float)


class AnalystRating(Base):
    """Analyst ratings and price targets"""
    __tablename__ = 'analyst_ratings'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    analyst_firm = Column(String(100))
    analyst_name = Column(String(100))
    rating = Column(String(20))
    rating_numeric = Column(Float)
    price_target = Column(Float)
    price_target_change = Column(Float)
    action = Column(String(20))


class Signal(Base):
    """Buy/Sell signals generated by the system"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    signal_date = Column(DateTime, nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)
    signal_strength = Column(String(20))
    composite_score = Column(Float)
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    momentum_score = Column(Float)
    confidence = Column(Float)
    primary_reason = Column(Text)
    contributing_factors = Column(JSON)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit_1 = Column(Float)
    take_profit_2 = Column(Float)
    is_active = Column(Boolean, default=True)
    exit_date = Column(DateTime)
    exit_price = Column(Float)
    exit_reason = Column(String(100))
    pnl_pct = Column(Float)
    explanation = Column(Text)
    implied_volatility = Column(Float)
    cc_premium_estimate = Column(Float)

    stock = relationship("Stock", back_populates="signals")


class DailyScore(Base):
    """Daily aggregate scores for each stock"""
    __tablename__ = 'daily_scores'
    
    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    technical_score = Column(Float)
    fundamental_score = Column(Float)
    sentiment_score = Column(Float)
    momentum_score = Column(Float)
    quality_score = Column(Float)
    composite_score = Column(Float)
    percentile_rank = Column(Float)
    is_overbought = Column(Boolean)
    is_oversold = Column(Boolean)
    has_strong_momentum = Column(Boolean)
    has_earnings_soon = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)


class Portfolio(Base):
    """Track simulated or live portfolio positions"""
    __tablename__ = 'portfolio'

    id = Column(Integer, primary_key=True)
    stock_id = Column(Integer, ForeignKey('stocks.id'), nullable=False)
    entry_date = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    shares = Column(Float, nullable=False)
    position_value = Column(Float)
    is_open = Column(Boolean, default=True)
    exit_date = Column(DateTime)
    exit_price = Column(Float)
    current_price = Column(Float)
    unrealized_pnl = Column(Float)
    unrealized_pnl_pct = Column(Float)
    realized_pnl = Column(Float)
    realized_pnl_pct = Column(Float)
    stop_loss_price = Column(Float)
    take_profit_price = Column(Float)
    signal_id = Column(Integer, ForeignKey('signals.id'))
    notes = Column(Text)
    is_paper_trade = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('app_users.id'))


class User(Base):
    """API users with free/premium tiers"""
    __tablename__ = 'app_users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    tier = Column(String(20), default='free')  # 'free' | 'premium'
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_database_url():
    """
    Get database URL with correct priority:
    1. Streamlit secrets (when running on Streamlit Cloud)
    2. Environment variable from .env (when running locally)
    3. SQLite fallback
    """
    # Try Streamlit secrets first
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
            url = st.secrets['DATABASE_URL']
            if url:
                return url
    except Exception:
        pass

    # Fall back to environment variable
    url = os.getenv('DATABASE_URL', 'sqlite:///./quant_screener.db')
    return url


def get_engine(database_url=None):
    """Create database engine - supports SQLite (local) and PostgreSQL (cloud)"""
    if database_url is None:
        database_url = get_database_url()

    # Fix postgres:// → postgresql:// (Supabase/Heroku format)
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    return create_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,  # Recycle connections every 30 min
        pool_pre_ping=True,  # Test connection before using it
    )


def create_tables(engine=None):
    """Create all tables"""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    print("[OK] Database tables created successfully")


def get_session(engine=None):
    """Get database session"""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_database():
    """Initialize database with schema"""
    engine = get_engine()
    create_tables(engine)
    return engine


if __name__ == "__main__":
    print("[BUILD] Initializing database...")
    engine = init_database()
    print("[OK] Database initialized successfully!")
    print("\n[DATA] Created tables:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")
