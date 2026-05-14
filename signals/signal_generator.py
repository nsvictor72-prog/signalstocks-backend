"""
Signal Generation Engine
Combines technical, fundamental, and sentiment data to generate BUY/SELL signals
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_session, Stock, PriceData, Fundamentals, Signal, DailyScore


class SignalGenerator:
    """Generate trading signals based on multi-factor analysis"""
    
    def __init__(self, session=None):
        self.session = session or get_session()
        
        # Signal thresholds (can be configured)
        self.BUY_THRESHOLD = 70
        self.STRONG_BUY_THRESHOLD = 80
        self.SELL_THRESHOLD = 30
        self.CONFIDENCE_THRESHOLD = 75
    
    def calculate_technical_score(self, ticker: str) -> Tuple[float, List[str]]:
        """
        Calculate technical score (0-100) based on price action and indicators
        
        Returns: (score, list of reasons)
        """
        try:
            stock = self.session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 50, ["Stock not found"]
            
            # Get latest price data with indicators
            latest = self.session.query(PriceData).filter_by(
                stock_id=stock.id
            ).order_by(PriceData.date.desc()).first()
            
            if not latest:
                return 50, ["No price data"]
            
            score = 0
            reasons = []
            
            # === TREND ANALYSIS (30 points) ===
            if latest.close and latest.sma_200:
                if latest.close > latest.sma_200:
                    score += 15
                    reasons.append("Above 200-day MA")
                    
            if latest.close and latest.sma_50 and latest.sma_200:
                if latest.close > latest.sma_50 > latest.sma_200:
                    score += 15
                    reasons.append("Golden cross formation")
            
            # === MOMENTUM ANALYSIS (30 points) ===
            if latest.rsi:
                if 40 <= latest.rsi <= 60:
                    score += 15
                    reasons.append("RSI in optimal zone")
                elif latest.rsi < 30:
                    score += 20
                    reasons.append("RSI oversold (buying opportunity)")
                elif latest.rsi > 70:
                    score -= 15
                    reasons.append("RSI overbought (risk)")
            
            if latest.macd_hist:
                if latest.macd_hist > 0:
                    score += 15
                    reasons.append("MACD bullish")
                else:
                    score -= 10
            
            # === VOLATILITY ANALYSIS (20 points) ===
            if latest.bb_upper and latest.bb_lower and latest.close:
                bb_position = (latest.close - latest.bb_lower) / (latest.bb_upper - latest.bb_lower)
                if bb_position < 0.2:
                    score += 15
                    reasons.append("Near lower Bollinger Band")
                elif bb_position > 0.8:
                    score -= 15
                    reasons.append("Near upper Bollinger Band (overbought)")
                else:
                    score += 5
            
            # === VOLUME CONFIRMATION (20 points) ===
            # Get recent volume data
            recent_prices = self.session.query(PriceData).filter_by(
                stock_id=stock.id
            ).order_by(PriceData.date.desc()).limit(20).all()
            
            if len(recent_prices) >= 20:
                avg_volume = sum(p.volume for p in recent_prices[1:]) / 19
                if latest.volume > avg_volume * 1.5:
                    score += 15
                    reasons.append(f"High volume ({latest.volume/avg_volume:.1f}x avg)")
                elif latest.volume < avg_volume * 0.5:
                    score -= 10
                    reasons.append("Low volume (weak signal)")
            
            # Normalize score to 0-100
            score = max(0, min(100, score + 50))
            
            return score, reasons
            
        except Exception as e:
            print(f"[ERROR] Error calculating technical score for {ticker}: {str(e)}")
            return 50, ["Error in calculation"]
    
    def calculate_fundamental_score(self, ticker: str) -> Tuple[float, List[str]]:
        """
        Calculate fundamental score based on valuation, growth, profitability
        
        Returns: (score, list of reasons)
        """
        try:
            stock = self.session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 50, ["Stock not found"]
            
            # Get latest fundamentals
            latest = self.session.query(Fundamentals).filter_by(
                stock_id=stock.id
            ).order_by(Fundamentals.date.desc()).first()
            
            if not latest:
                return 50, ["No fundamental data"]
            
            score = 0
            reasons = []
            
            # === VALUATION (25 points) ===
            if latest.pe_ratio:
                if latest.pe_ratio < 15:
                    score += 20
                    reasons.append(f"Low P/E ({latest.pe_ratio:.1f})")
                elif 15 <= latest.pe_ratio <= 25:
                    score += 15
                    reasons.append(f"Fair P/E ({latest.pe_ratio:.1f})")
                elif latest.pe_ratio > 50:
                    score -= 10
                    reasons.append(f"High P/E ({latest.pe_ratio:.1f})")
            
            if latest.peg_ratio:
                if latest.peg_ratio < 1.0:
                    score += 15
                    reasons.append(f"Attractive PEG ({latest.peg_ratio:.2f})")
                elif latest.peg_ratio > 2.0:
                    score -= 10
            
            # === GROWTH (25 points) ===
            if latest.revenue_growth_yoy:
                if latest.revenue_growth_yoy > 0.30:
                    score += 20
                    reasons.append(f"Strong revenue growth ({latest.revenue_growth_yoy*100:.1f}%)")
                elif latest.revenue_growth_yoy > 0.15:
                    score += 15
                    reasons.append(f"Good revenue growth ({latest.revenue_growth_yoy*100:.1f}%)")
                elif latest.revenue_growth_yoy < 0:
                    score -= 15
                    reasons.append("Revenue declining")
            
            if latest.earnings_growth_yoy:
                if latest.earnings_growth_yoy > 0.25:
                    score += 15
                    reasons.append(f"Strong earnings growth ({latest.earnings_growth_yoy*100:.1f}%)")
            
            # === PROFITABILITY (25 points) ===
            if latest.net_margin:
                if latest.net_margin > 0.20:
                    score += 15
                    reasons.append(f"High profit margins ({latest.net_margin*100:.1f}%)")
                elif latest.net_margin < 0:
                    score -= 15
                    reasons.append("Unprofitable")
            
            if latest.roe:
                if latest.roe > 0.15:
                    score += 15
                    reasons.append(f"Strong ROE ({latest.roe*100:.1f}%)")
                elif latest.roe < 0:
                    score -= 10
            
            # === BALANCE SHEET (25 points) ===
            if latest.debt_to_equity:
                if latest.debt_to_equity < 0.5:
                    score += 15
                    reasons.append("Low debt")
                elif latest.debt_to_equity > 2.0:
                    score -= 15
                    reasons.append("High debt (risk)")
            
            if latest.current_ratio:
                if latest.current_ratio > 1.5:
                    score += 10
                    reasons.append("Strong liquidity")
            
            # Normalize
            score = max(0, min(100, score + 50))
            
            return score, reasons
            
        except Exception as e:
            print(f"[ERROR] Error calculating fundamental score for {ticker}: {str(e)}")
            return 50, ["Error in calculation"]
    
    def calculate_momentum_score(self, ticker: str) -> Tuple[float, List[str]]:
        """
        Calculate momentum score based on price action and relative strength
        
        Returns: (score, list of reasons)
        """
        try:
            stock = self.session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                return 50, []
            
            # Get price history
            prices = self.session.query(PriceData).filter_by(
                stock_id=stock.id
            ).order_by(PriceData.date.desc()).limit(60).all()
            
            if len(prices) < 20:
                return 50, ["Insufficient price history"]
            
            score = 0
            reasons = []
            
            # Calculate returns over different periods
            if len(prices) >= 5:
                ret_5d = ((prices[0].close - prices[4].close) / prices[4].close) * 100
                if ret_5d > 5:
                    score += 20
                    reasons.append(f"Strong 5-day momentum (+{ret_5d:.1f}%)")
                elif ret_5d < -5:
                    score -= 20
                    reasons.append(f"Weak 5-day momentum ({ret_5d:.1f}%)")
            
            if len(prices) >= 20:
                ret_20d = ((prices[0].close - prices[19].close) / prices[19].close) * 100
                if ret_20d > 10:
                    score += 25
                    reasons.append(f"Strong 20-day momentum (+{ret_20d:.1f}%)")
                elif ret_20d < -10:
                    score -= 25
            
            if len(prices) >= 60:
                ret_60d = ((prices[0].close - prices[59].close) / prices[59].close) * 100
                if ret_60d > 20:
                    score += 30
                    reasons.append(f"Strong 60-day trend (+{ret_60d:.1f}%)")
            
            # Check for consistent uptrend
            if len(prices) >= 10:
                recent_highs = [p.close for p in prices[:10]]
                if all(recent_highs[i] >= recent_highs[i+1] for i in range(len(recent_highs)-1)):
                    score += 15
                    reasons.append("Consistent uptrend")
            
            # Normalize
            score = max(0, min(100, score + 50))
            
            return score, reasons
            
        except Exception as e:
            return 50, ["Error in calculation"]
    
    # Industries with poor performance — skip in live signals too
    AVOID_INDUSTRIES = {
        'Semiconductor Equipment & Materials',
        'Biotechnology',
        'Medical Devices',
        'Communication Equipment',
        'Asset Management',
    }

    def generate_composite_signal(self, ticker: str) -> Dict:
        """
        Generate final BUY/SELL signal combining all factors
        
        Returns dict with signal details
        """
        print(f"\n🔍 Analyzing {ticker}...")
        
        try:
            # Check sector filter first
            stock = self.session.query(Stock).filter_by(ticker=ticker).first()
            if stock and stock.industry in self.AVOID_INDUSTRIES:
                print(f"[SKIP] {ticker} — {stock.industry} (sector filtered)")
                return {}

            # Calculate individual scores
            tech_score, tech_reasons = self.calculate_technical_score(ticker)
            fund_score, fund_reasons = self.calculate_fundamental_score(ticker)
            momentum_score, momentum_reasons = self.calculate_momentum_score(ticker)

            # Phase 1: Volume spike + Earnings risk
            from src.signals.phase1_factors import calculate_volume_score, calculate_earnings_risk
            volume_adj, volume_reasons = calculate_volume_score(ticker, self.session)
            earnings_adj, earnings_reasons = calculate_earnings_risk(ticker)

            # Phase 2: News sentiment + Insider buying + Short squeeze
            from src.signals.phase2_factors import (
                calculate_news_sentiment,
                calculate_insider_score,
                calculate_short_squeeze_score
            )
            news_adj,     news_reasons     = calculate_news_sentiment(ticker)
            insider_adj,  insider_reasons  = calculate_insider_score(ticker)
            squeeze_adj,  squeeze_reasons  = calculate_short_squeeze_score(ticker)

            # Phase 3: Support & Resistance
            from src.signals.support_resistance import calculate_sr_score
            sr_adj, sr_reasons = calculate_sr_score(ticker, self.session)

            # Apply volume adjustment to technical score
            tech_score = max(0, min(100, tech_score + volume_adj))

            # Weighted composite score
            composite_score = (
                tech_score * 0.40 +
                fund_score * 0.35 +
                momentum_score * 0.25
            )

            # Apply all adjustments
            composite_score = (
                composite_score
                + earnings_adj
                + news_adj
                + insider_adj
                + squeeze_adj
                + sr_adj
            )
            
            # Normalize to 0-95 range (cap at 95, not 100)
            composite_score = max(0, min(95, composite_score))

            # Calculate confidence
            scores = [tech_score, fund_score, momentum_score]
            score_std = np.std(scores)
            confidence = max(50, 100 - score_std)

            # Reduce confidence if earnings imminent
            if earnings_adj <= -15:
                confidence = min(confidence, 60)

            # Boost confidence if multiple smart money signals agree
            smart_money = sum([
                1 if insider_adj > 0 else 0,
                1 if squeeze_adj > 10 else 0,
                1 if news_adj > 0 else 0,
            ])
            if smart_money >= 2:
                confidence = min(100, confidence + 5)
            
            # Determine signal type
            if composite_score >= self.STRONG_BUY_THRESHOLD and confidence >= self.CONFIDENCE_THRESHOLD:
                signal_type = 'STRONG_BUY'
                signal_strength = 'STRONG'
            elif composite_score >= self.BUY_THRESHOLD:
                signal_type = 'BUY'
                signal_strength = 'MODERATE'
            elif composite_score <= self.SELL_THRESHOLD:
                signal_type = 'SELL'
                signal_strength = 'STRONG' if composite_score < 20 else 'MODERATE'
            else:
                signal_type = 'HOLD'
                signal_strength = 'WEAK'
            
            # Get current price for entry/exit levels
            stock = self.session.query(Stock).filter_by(ticker=ticker).first()
            latest_price = self.session.query(PriceData).filter_by(
                stock_id=stock.id
            ).order_by(PriceData.date.desc()).first()
            
            entry_price = latest_price.close if latest_price else None
            
            # Calculate stop-loss and take-profit levels
            if entry_price:
                stop_loss = entry_price * 0.93  # 7% stop-loss
                take_profit_1 = entry_price * 1.15  # 15% profit target
                take_profit_2 = entry_price * 1.30  # 30% profit target
            else:
                stop_loss = take_profit_1 = take_profit_2 = None
            
            # Combine all reasons
            # Put actionable warnings first (S/R, earnings, news), then technical reasons
            all_reasons = sr_reasons + earnings_reasons + news_reasons + insider_reasons + squeeze_reasons + tech_reasons + fund_reasons + momentum_reasons + volume_reasons
            primary_reason = all_reasons[0] if all_reasons else "Multi-factor analysis"
            
            signal = {
                'ticker': ticker,
                'signal_type': signal_type,
                'signal_strength': signal_strength,
                'composite_score': round(composite_score, 1),
                'technical_score': round(tech_score, 1),
                'fundamental_score': round(fund_score, 1),
                'momentum_score': round(momentum_score, 1),
                'confidence': round(confidence, 1),
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'primary_reason': primary_reason,
                'all_reasons': all_reasons[:8],  # Top 8 reasons
                'date': datetime.utcnow()
            }
            
            # Print signal summary
            emoji = '[BUY]' if 'BUY' in signal_type else '[SELL]' if signal_type == 'SELL' else '[HOLD]'
            print(f"{emoji} {signal_type} - Score: {composite_score:.0f}/100 | Confidence: {confidence:.0f}%")
            
            return signal
            
        except Exception as e:
            print(f"[ERROR] Error generating signal for {ticker}: {str(e)}")
            return {}
    
    def save_signal(self, signal_data: Dict) -> bool:
        """Save signal to database — deactivates old signals first"""
        if not signal_data:
            return False
        
        try:
            stock = self.session.query(Stock).filter_by(ticker=signal_data['ticker']).first()
            if not stock:
                return False

            # Deactivate all existing active signals for this stock
            self.session.query(Signal).filter_by(
                stock_id=stock.id,
                is_active=True
            ).update({'is_active': False}, synchronize_session=False)
            
            # Helper to safely convert numpy types to plain Python floats
            def to_float(val):
                if val is None:
                    return None
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return None

            # Create new signal record
            signal = Signal(
                stock_id=stock.id,
                signal_date=signal_data['date'],
                signal_type=signal_data['signal_type'],
                signal_strength=signal_data['signal_strength'],
                composite_score=to_float(signal_data['composite_score']),
                technical_score=to_float(signal_data['technical_score']),
                fundamental_score=to_float(signal_data['fundamental_score']),
                momentum_score=to_float(signal_data['momentum_score']),
                confidence=to_float(signal_data['confidence']),
                entry_price=to_float(signal_data['entry_price']),
                stop_loss=to_float(signal_data['stop_loss']),
                take_profit_1=to_float(signal_data['take_profit_1']),
                take_profit_2=to_float(signal_data['take_profit_2']),
                primary_reason=signal_data['primary_reason'],
                contributing_factors=signal_data['all_reasons'],
                is_active=True
            )
            
            self.session.add(signal)
            self.session.commit()
            return True
            
        except Exception as e:
            print(f"[ERROR] Error saving signal: {str(e)}")
            self.session.rollback()
            return False


    def generate_signals_for_universe(self, tickers: List[str]) -> pd.DataFrame:
        """Generate signals for all stocks in universe"""
        print(f"\n{'='*60}")
        print(f"[TARGET] GENERATING TRADING SIGNALS ({len(tickers)} stocks)")
        print(f"{'='*60}")
        
        all_signals = []
        
        for i, ticker in enumerate(tickers, 1):
            print(f"\n[{i}/{len(tickers)}]", end=" ")
            signal = self.generate_composite_signal(ticker)
            
            if signal:
                all_signals.append(signal)
                self.save_signal(signal)
        
        # Create DataFrame for analysis
        df = pd.DataFrame(all_signals)
        
        if not df.empty:
            # Sort by composite score
            df = df.sort_values('composite_score', ascending=False)
            
            # Print summary
            print(f"\n{'='*60}")
            print(f"[DATA] SIGNAL SUMMARY")
            print(f"{'='*60}")
            
            buy_signals = df[df['signal_type'].str.contains('BUY')]
            sell_signals = df[df['signal_type'] == 'SELL']
            hold_signals = df[df['signal_type'] == 'HOLD']
            
            print(f"\n[BUY] BUY Signals: {len(buy_signals)}")
            if len(buy_signals) > 0:
                print("\nTop 5 BUY Opportunities:")
                for idx, row in buy_signals.head(5).iterrows():
                    print(f"  {row['ticker']:6s} - Score: {row['composite_score']:5.1f} | "
                          f"Conf: {row['confidence']:5.1f}% | ${row['entry_price']:.2f}")
            
            print(f"\n[SELL] SELL Signals: {len(sell_signals)}")
            if len(sell_signals) > 0:
                for idx, row in sell_signals.head(3).iterrows():
                    print(f"  {row['ticker']:6s} - Score: {row['composite_score']:5.1f}")
            
            print(f"\n[HOLD] HOLD Signals: {len(hold_signals)}")
            
        return df


def main():
    """Test signal generation"""
    # Test with a few stocks
    tickers = ['NVDA', 'PLTR', 'IONQ', 'TSLA', 'AAPL']
    
    generator = SignalGenerator()
    signals_df = generator.generate_signals_for_universe(tickers)
    
    if not signals_df.empty:
        print(f"\n{'='*60}")
        print("[OK] Signals generated successfully!")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
