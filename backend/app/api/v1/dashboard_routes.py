from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import AdminDashboardData, HrDashboardData
from app.services import dashboard_service

from fastapi.responses import Response

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/admin", response_model=AdminDashboardData)
def get_admin_dashboard(
    range: str = "30d",
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
        
    return dashboard_service.get_admin_dashboard_data(db, date_range=range)

@router.get("/hr", response_model=HrDashboardData)
def get_hr_dashboard(
    range: str = "30d",
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
        
    return dashboard_service.get_hr_dashboard_data(db, date_range=range)

@router.get("/export")
def export_dashboard_report(
    card_type: str = "employees",
    range: str = "30d",
    format: str = "pdf",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate PDF or CSV export for dashboard metrics (employees, attendance, leaves, payroll).
    """
    if not current_user.role or current_user.role.name.lower() not in ["admin", "hr"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to export dashboard data"
        )
    
    if format.lower() == "pdf":
        pdf_bytes = dashboard_service.generate_dashboard_pdf_export(db, card_type, range)
        filename = f"{card_type}_report_{range}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    else:
        csv_content = dashboard_service.generate_dashboard_csv_export(db, card_type, range)
        filename = f"{card_type}_report_{range}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )





