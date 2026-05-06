from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app import models
from app.seeds.seed_demo_attendance import seed_attendance
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles
from app.api.v1 import (
    auth_routes,
    profile_routes,
    employee_routes,
    attendance_routes,
    hr_routes,
    dashboard_routes,
    timeoff_routes,
)

from app.core.websocket_manager import manager
from app.services.scheduler_service import start_scheduler, shutdown_scheduler

app = FastAPI(title=settings.PROJECT_NAME)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.on_event("startup")
def startup():
    # Ensure all SQLAlchemy models are registered before creating tables.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_roles(db)
        seed_users(db)
        seed_attendance(db)
    finally:
        db.close()
    start_scheduler()

@app.on_event("shutdown")
def shutdown():
    shutdown_scheduler()

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
app.include_router(timeoff_routes.router, prefix="/api/v1")

