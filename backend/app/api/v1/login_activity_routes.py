from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.login_activity import LoginActivityResponse
from app.services import login_activity_service

router = APIRouter(prefix="/login-activity", tags=["login-activity"])

@router.get("", response_model=List[LoginActivityResponse])
def get_login_history(
    filter_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    role = current_user.role.name.lower() if current_user.role else ""
    exclude_admin = False
    if role == "admin":
        target_user_id = user_id
    elif role == "hr":
        target_user_id = user_id
        exclude_admin = True
    else:
        target_user_id = current_user.id

    return login_activity_service.get_login_activities_with_names(
        db=db,
        filter_type=filter_type,
        start_date=start_date,
        end_date=end_date,
        user_id=target_user_id,
        exclude_admin=exclude_admin
    )

@router.get("/{id}", response_model=LoginActivityResponse)
def get_login_detail(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    activity = login_activity_service.get_login_activity_by_id(db, id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Login activity record not found"
        )
        
    role = current_user.role.name.lower() if current_user.role else ""
    if role == "hr":
        from app.models.user import User as UserModel
        user = db.query(UserModel).filter(UserModel.id == activity.user_id).first()
        if user and user.role and user.role.name.lower() == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to view this login activity record"
            )
            
    if role not in ["admin", "hr"] and activity.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this login activity record"
        )
        
    return activity
