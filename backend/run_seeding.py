from app.core.database import SessionLocal
from app.seeds.seed_demo_users import seed_users

db = SessionLocal()
try:
    seed_users(db)
    print("Database seeding completed successfully!")
finally:
    db.close()
