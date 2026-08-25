from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app import models
from app.seeds.seed_demo_users import seed_users
from app.seeds.seed_master_data import seed_roles, seed_master_data
from app.core.websocket_manager import manager
from app.services.scheduler_service import start_scheduler, shutdown_scheduler

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
    document_routes,
    training_routes,
)

logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.domain.notifications.subscriber import register_all_listeners
    register_all_listeners()

    if settings.AUTO_CREATE_TABLES and settings.APP_ENV != "test":
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
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    # Browsers cannot set Authorization headers during a WebSocket upgrade.
    # A short-lived ticket is therefore sent in the Sec-WebSocket-Protocol
    # header, rather than in the URL where it could be logged.
    from app.api.deps import get_ws_user
    requested_protocols = [
        value.strip()
        for value in websocket.headers.get("sec-websocket-protocol", "").split(",")
        if value.strip()
    ]
    ticket = requested_protocols[1] if len(requested_protocols) >= 2 and requested_protocols[0] == "hrms-ticket" else None
    db = SessionLocal()
    try:
        user = get_ws_user(ticket=ticket, db=db)
        if not user or user.id != user_id:
            logger.warning("WebSocket auth failed for user_id=%s", user_id)
            await websocket.accept()  # Must accept before closing with code in some runtimes
            await websocket.close(code=4001)
            return
    except Exception:
        logger.exception("WebSocket auth exception for user_id=%s", user_id)
        await websocket.accept()
        await websocket.close(code=4001)
        return
    finally:
        db.close()

    logger.info("WebSocket connection established for user_id=%s", user_id)
    await manager.connect(websocket, user_id, subprotocol="hrms-ticket")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception: %s", exc)
    if settings.APP_ENV == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal server error occurred. Please contact system administrator."}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
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
app.include_router(document_routes.router, prefix="/api/v1")
app.include_router(training_routes.router, prefix="/api/v1")

