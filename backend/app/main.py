from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app import models
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles
from app.api.v1 import hr_routes, employee_routes
from app.api.v1 import (
    auth_routes, 
    profile_routes, 
    employee_routes, 
    attendance_routes, 
    hr_routes, 
    dashboard_routes
)

app = FastAPI(title=settings.PROJECT_NAME)

@app.on_event("startup")
def startup():
    # Ensure all SQLAlchemy models are registered before creating tables.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_users(db)
    finally:
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is running and CORS is enabled"}

app.include_router(auth_routes.router, prefix="/api/v1")
app.include_router(profile_routes.router, prefix="/api/v1")
app.include_router(employee_routes.router, prefix="/api/v1")
app.include_router(attendance_routes.router, prefix="/api/v1")
app.include_router(hr_routes.router, prefix="/api/v1")
app.include_router(dashboard_routes.router, prefix="/api/v1")


