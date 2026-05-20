from sqlalchemy import text
from database import get_session

def run_migration():
    session = get_session()
    
    try:
        print("Adding updated_at column to app_users...")
        
        session.execute(text("""
            ALTER TABLE app_users 
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))
        
        session.commit()
        print("✅ Migration complete")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    run_migration()
