from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
import logging
import jwt
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user
from app.models.user import User
from app.models.rate_limit import RateLimitRecord
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    ChangePasswordRequest,
    StandardResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    WebSocketTicketResponse,
)
from app.core.security import create_websocket_ticket
from app.services import auth_service
from app.services.login_activity_service import log_login_activity

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _client_ip(request: Request) -> str:
    # Prioritize X-Real-IP set by trusted reverse proxy (Nginx)
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


def _rate_limit_key(prefix: str, request: Request, email: str) -> str:
    return f"{prefix}:{_client_ip(request)}:{email.strip().lower()}"


def _enforce_rate_limit(
    db: Session,
    key: str,
    max_attempts: int,
    window_seconds: int,
    lockout_seconds: int
) -> None:
    now = datetime.now(timezone.utc)
    rec = db.query(RateLimitRecord).filter(RateLimitRecord.key == key).first()

    if rec:
        lu = rec.locked_until
        if lu and lu.tzinfo is None:
            lu = lu.replace(tzinfo=timezone.utc)
        if lu and lu > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts. Please wait before trying again.",
            )
        window_start = now - timedelta(seconds=window_seconds)
        ws = rec.window_start
        if ws and ws.tzinfo is None:
            ws = ws.replace(tzinfo=timezone.utc)
        if ws < window_start:
            rec.window_start = now
            rec.attempts = 1
            rec.locked_until = None
        else:
            rec.attempts += 1
            if rec.attempts > max_attempts:
                rec.locked_until = now + timedelta(seconds=lockout_seconds)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please wait before trying again.",
                )
        db.commit()
    else:
        new_rec = RateLimitRecord(
            key=key,
            attempts=1,
            window_start=now,
            locked_until=None,
        )
        db.add(new_rec)
        try:
            db.commit()
        except Exception:
            db.rollback()


def _clear_rate_limit(db: Session, key: str) -> None:
    try:
        db.query(RateLimitRecord).filter(RateLimitRecord.key == key).delete()
        db.commit()
    except Exception:
        db.rollback()


@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    client_ip = _client_ip(request)
    # Global IP rate limit (prevents distributed email attacks from same source IP)
    _enforce_rate_limit(db, f"login_ip:{client_ip}", max_attempts=30, window_seconds=300, lockout_seconds=900)
    # Specific account rate limit
    login_key = _rate_limit_key("login", request, payload.email)
    _enforce_rate_limit(db, login_key, max_attempts=5, window_seconds=300, lockout_seconds=900)
    result = auth_service.authenticate_user(db, payload)
    
    ip_address = _client_ip(request)
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
        _clear_rate_limit(db, login_key)
        # Update last_login_ip
        logged_user = db.query(User).filter(User.id == user_id).first()
        if logged_user:
            logged_user.last_login_ip = ip_address
            db.commit()

        await log_login_activity(
            db=db,
            user_id=user_id,
            ip_address=ip_address,
            user_agent_string=user_agent,
            status="Success"
        )
        # Provide cookie for single-context/legacy browsers, while keeping accessToken
        # in the response body so clients can isolate sessions per tab via sessionStorage
        # and Bearer headers without cross-tab session contamination.
        access_token = result.get("accessToken")
        if access_token:
            response.set_cookie(
                key=settings.SESSION_COOKIE_NAME,
                value=access_token,
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite="lax",
                path="/",
            )
        
    return result


@router.post("/logout", response_model=StandardResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    # Invalidate session cookie
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    # Revoke JWT session globally by incrementing token_version
    token = request.headers.get("authorization")
    if token and token.lower().startswith("bearer "):
        token = token[7:].strip()
    else:
        token = request.cookies.get(settings.SESSION_COOKIE_NAME)

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email = payload.get("sub")
            if email:
                user = db.query(User).filter(User.email == email).first()
                if user:
                    user.token_version = (user.token_version or 1) + 1
                    db.commit()
        except Exception:
            pass

    return {"success": True, "message": "Signed out successfully."}


@router.post("/change-password", response_model=StandardResponse)
def change_password(
    request: ChangePasswordRequest, 
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    change_key = _rate_limit_key("change-password", http_request, current_user.email)
    _enforce_rate_limit(db, change_key, max_attempts=5, window_seconds=300, lockout_seconds=900)
    result = auth_service.change_user_password(db, current_user.id, request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    _clear_rate_limit(db, change_key)
    return result


@router.post("/forgot-password", response_model=StandardResponse)
def forgot_password(payload: ForgotPasswordRequest, http_request: Request, db: Session = Depends(get_db)):
    client_ip = _client_ip(http_request)
    _enforce_rate_limit(db, f"forgot_ip:{client_ip}", max_attempts=20, window_seconds=300, lockout_seconds=900)
    reset_key = _rate_limit_key("forgot-password", http_request, payload.email)
    _enforce_rate_limit(db, reset_key, max_attempts=5, window_seconds=300, lockout_seconds=900)
    auth_service.forgot_password(db, payload)
    return {"success": True, "message": "If the account exists, password reset instructions have been sent to the registered email."}


@router.post("/reset-password", response_model=StandardResponse)
def reset_password(request: ResetPasswordRequest, http_request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(http_request)
    reset_rate_key = f"reset-password:{ip}"
    _enforce_rate_limit(db, reset_rate_key, max_attempts=10, window_seconds=300, lockout_seconds=900)
    result = auth_service.reset_password(db, request)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.post("/ws-ticket", response_model=WebSocketTicketResponse)
def create_ws_ticket(current_user: User = Depends(get_current_user)):
    """Issue a one-minute ticket for the WebSocket subprotocol handshake."""
    return {"ticket": create_websocket_ticket(current_user.email, current_user.id)}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "displayName": current_user.display_name,
        "role": current_user.role.name.lower() if current_user.role else "employee",
        "linkedEmployeeId": current_user.linked_employee_id,
        "linkedHrId": current_user.linked_hr_id,
        "status": current_user.status,
        "accessibleDashboards": current_user.accessibleDashboards,
        "isManager": current_user.is_manager,
    }
