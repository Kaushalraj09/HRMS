import sys
import os

# Adjust sys.path to find 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import create_engine, text
from app.core.config import settings

def run_migration():
    print(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]}")
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as conn:
        print("Checking if 'profile_image' column exists in 'users' table...")
        
        # Safe alter table statement for PostgreSQL
        conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS profile_image TEXT;"))
        conn.commit()
        
        print("Successfully added (or verified) 'profile_image' column in 'users' table!")

if __name__ == "__main__":
    run_migration()
