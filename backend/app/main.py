from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app import models
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles
from app.api.v1 import (
    auth_routes,
    profile_routes,
    employee_routes,
    attendance_routes,
    hr_routes,
    dashboard_routes,
    notification_routes,
    login_activity_routes,
    timeoff_routes,
)

from app.core.websocket_manager import manager
from app.services.scheduler_service import start_scheduler, shutdown_scheduler

app = FastAPI(title=settings.PROJECT_NAME)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    print(f"WebSocket connection attempt from user {user_id}")
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

@app.on_event("startup")
def startup():
    if settings.AUTO_CREATE_TABLES:
        # Development convenience only. Production should rely on managed migrations.
        Base.metadata.create_all(bind=engine)

    if settings.AUTO_SEED_ROLES or settings.AUTO_SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            if settings.AUTO_SEED_ROLES:
                seed_roles(db)
            if settings.AUTO_SEED_DEMO_DATA:
                seed_users(db)
        finally:
            db.close()

    if settings.ENABLE_SCHEDULER:
        start_scheduler()

@app.on_event("shutdown")
def shutdown():
    if settings.ENABLE_SCHEDULER:
        shutdown_scheduler()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
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
app.include_router(notification_routes.router, prefix="/api/v1")
app.include_router(login_activity_routes.router, prefix="/api/v1")
app.include_router(timeoff_routes.router, prefix="/api/v1")
