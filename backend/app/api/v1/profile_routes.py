from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services import profile_service
from app.schemas.profile import EmployeeProfile, ProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])

@router.get("/", response_model=EmployeeProfile)
def read_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    profile = profile_service.get_employee_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.put("/update")
def update_profile(
    payload: ProfileUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    result = profile_service.update_employee_profile(db, current_user.id, payload)
    if not result:
        raise HTTPException(status_code=400, detail="Update failed")
    return result
