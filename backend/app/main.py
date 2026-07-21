from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app import models
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles, seed_master_data
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
    regularization_routes,
    report_routes,
    master_data_routes,
    approval_routes,
)

from contextlib import asynccontextmanager
from app.core.websocket_manager import manager
from app.services.scheduler_service import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.notifications.subscriber import register_all_listeners
    register_all_listeners()

    if settings.AUTO_CREATE_TABLES:
        # Run Alembic migrations programmatically to set up/upgrade the database schema
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")

    if settings.AUTO_SEED_ROLES or settings.AUTO_SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            if settings.AUTO_SEED_ROLES:
                seed_roles(db)
                seed_master_data(db)
            if settings.AUTO_SEED_DEMO_DATA:
                seed_users(db)
        finally:
            db.close()

    if settings.ENABLE_SCHEDULER:
        start_scheduler()

    yield

    if settings.ENABLE_SCHEDULER:
        shutdown_scheduler()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, token: str = None):
    # Authenticate token if present, or extract from query parameters
    from app.api.deps import get_ws_user
    db = SessionLocal()
    try:
        # Validate WebSocket token
        user = get_ws_user(token=token, db=db)
        if not user or user.id != user_id:
            print(f"WebSocket auth failed: user mismatch or invalid token for user {user_id}")
            await websocket.accept()  # Must accept before closing with code in some runtimes
            await websocket.close(code=4001)
            return
    except Exception as e:
        print(f"WebSocket auth exception for user {user_id}: {e}")
        await websocket.accept()
        await websocket.close(code=4001)
        return
    finally:
        db.close()

    print(f"WebSocket connection attempt from user {user_id}")
    await manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)



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
app.include_router(regularization_routes.router, prefix="/api/v1")
app.include_router(report_routes.router, prefix="/api/v1")
app.include_router(master_data_routes.router, prefix="/api/v1")
app.include_router(approval_routes.router, prefix="/api/v1")
