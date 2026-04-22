from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
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


