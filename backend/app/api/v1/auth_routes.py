from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest, StandardResponse
from app.schemas.forgot_password import ForgotPasswordRequest, ResetPasswordRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.authenticate_user(db, request)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    return result

@router.post("/change-password", response_model=StandardResponse)
def change_password(
    request: ChangePasswordRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = auth_service.change_user_password(db, current_user.id, request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result

@router.post("/forgot-password", response_model=StandardResponse)
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    reset_link = auth_service.forgot_password(db, request)
    if not reset_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Official email or username is not registered."
        )
    return {"success": True, "message": f"Password reset link generated. Reset Link: {reset_link}"}

@router.post("/reset-password", response_model=StandardResponse)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    result = auth_service.reset_password(db, request)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


