from app.core.database import SessionLocal
from app.seeds.seed_master_data import seed_roles, seed_master_data
from app.seeds.seed_demo_users import seed_users

db = SessionLocal()
try:
    seed_roles(db)
    seed_master_data(db)
    seed_users(db)
    print("Database seeding completed successfully!")
finally:
    db.close()

