from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest, StandardResponse, ForgotPasswordRequest, ResetPasswordRequest
from app.services import auth_service
from app.services.login_activity_service import log_login_activity

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    result = auth_service.authenticate_user(db, payload)
    
    ip_address = request.client.host if request.client else "0.0.0.0"
    user_agent = request.headers.get("user-agent", "Unknown Agent")
    
    if not result:
        # Attempt to log failed activity if email is valid user
        user = db.query(User).filter(User.email.ilike(payload.email)).first()
        if user:
            await log_login_activity(
                db=db,
                user_id=user.id,
                ip_address=ip_address,
                user_agent_string=user_agent,
                status="Failed"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    user_id = result.get("me", {}).get("id")
    if user_id and "accessToken" in result:
        await log_login_activity(
            db=db,
            user_id=user_id,
            ip_address=ip_address,
            user_agent_string=user_agent,
            status="Success"
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
            detail="Email does not exist"
        )
    if settings.EXPOSE_RESET_LINK_IN_RESPONSE:
        return {"success": True, "message": f"Password reset link generated. Reset Link: {reset_link}"}
    return {"success": True, "message": "Password reset link generated and sent successfully."}

@router.post("/reset-password", response_model=StandardResponse)
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    result = auth_service.reset_password(db, request)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result

