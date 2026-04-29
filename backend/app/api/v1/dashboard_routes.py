from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import AdminDashboardData, HrDashboardData
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/admin", response_model=AdminDashboardData)
def get_admin_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get statistics and recent data for the admin dashboard.
    """
    if not current_user.role or current_user.role.name.lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access the admin dashboard"
        )
        
    return dashboard_service.get_admin_dashboard_data(db)

@router.get("/hr", response_model=HrDashboardData)
def get_hr_dashboard(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Get workforce statistics and attendance breakdowns for the HR dashboard.
    """
    if not current_user.role or current_user.role.name.lower() not in ["hr", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access the HR dashboard"
        )
        
    return dashboard_service.get_hr_dashboard_data(db)


