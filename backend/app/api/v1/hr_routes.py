from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.core.enums import UserRole
from app.schemas.hr import HrCreate, HrResponse
from app.services import hr_service

router = APIRouter(prefix="/hr-users", tags=["hr-management"])

@router.post("", response_model=HrResponse)
def create_hr_user(
    request: HrCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators are authorized to manage HR users"
        )
    try:
        return hr_service.create_hr(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("", response_model=List[HrResponse])
def get_hr_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role or current_user.role.name.lower() != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators are authorized to view HR users"
        )
    return hr_service.list_hrs(db)

