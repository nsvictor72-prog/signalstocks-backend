"""
Signal generation with proper connection cleanup
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signals.signal_generator import SignalGenerator
from database import get_session, Stock

def main():
    session = get_session()
    
    try:
        generator = SignalGenerator(session)
        stocks = session.query(Stock.ticker).all()
        
        print(f"Processing {len(stocks)} stocks...")
        
        for i, stock in enumerate(stocks):
            try:
                signal = generator.generate_composite_signal(stock.ticker)
                generator.save_signal(signal)
                
                # Commit and close connection every 50 stocks
                if i % 50 == 0:
                    session.commit()
                    session.close()
                    session = get_session()
                    generator.session = session
                    print(f"Progress: {i}/{len(stocks)}")
                    
            except Exception as e:
                print(f"Error on {stock.ticker}: {e}")
                continue
        
        session.commit()
        print("✅ Complete")
        
    finally:
        session.close()

if __name__ == "__main__":
    main()
