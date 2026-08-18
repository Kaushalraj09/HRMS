from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest, StandardResponse, ForgotPasswordRequest, ResetPasswordRequest, WebSocketTicketResponse
from app.core.security import create_websocket_ticket
from app.services import auth_service
from app.services.login_activity_service import log_login_activity

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_attempts: dict[str, deque[datetime]] = defaultdict(deque)
_lockouts: dict[str, datetime] = {}


def _client_ip(request: Request) -> str:
    # Prioritize X-Real-IP set by trusted reverse proxy (Nginx)
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()
    return request.client.host if request.client else "0.0.0.0"


def _rate_limit_key(prefix: str, request: Request, email: str) -> str:
    return f"{prefix}:{_client_ip(request)}:{email.strip().lower()}"


def _enforce_rate_limit(key: str, max_attempts: int, window_seconds: int, lockout_seconds: int) -> None:
    now = datetime.now(timezone.utc)
    locked_until = _lockouts.get(key)
    if locked_until and locked_until > now:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait before trying again.",
        )
    if locked_until:
        _lockouts.pop(key, None)

    window_start = now - timedelta(seconds=window_seconds)
    attempts = _attempts[key]
    while attempts and attempts[0] < window_start:
        attempts.popleft()
    if len(attempts) >= max_attempts:
        _lockouts[key] = now + timedelta(seconds=lockout_seconds)
        attempts.clear()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait before trying again.",
        )
    attempts.append(now)


def _clear_rate_limit(key: str) -> None:
    _attempts.pop(key, None)
    _lockouts.pop(key, None)

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    login_key = _rate_limit_key("login", request, payload.email)
    _enforce_rate_limit(login_key, max_attempts=5, window_seconds=300, lockout_seconds=900)
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
        _clear_rate_limit(login_key)
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
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    change_key = _rate_limit_key("change-password", http_request, current_user.email)
    _enforce_rate_limit(change_key, max_attempts=5, window_seconds=300, lockout_seconds=900)
    result = auth_service.change_user_password(db, current_user.id, request)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    _clear_rate_limit(change_key)
    return result

@router.post("/forgot-password", response_model=StandardResponse)
def forgot_password(payload: ForgotPasswordRequest, http_request: Request, db: Session = Depends(get_db)):
    reset_key = _rate_limit_key("forgot-password", http_request, payload.email)
    _enforce_rate_limit(reset_key, max_attempts=5, window_seconds=300, lockout_seconds=900)
    auth_service.forgot_password(db, payload)
    return {"success": True, "message": "If the account exists, password reset instructions have been sent to the registered email."}

@router.post("/reset-password", response_model=StandardResponse)
def reset_password(request: ResetPasswordRequest, http_request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(http_request)
    reset_rate_key = f"reset-password:{ip}"
    _enforce_rate_limit(reset_rate_key, max_attempts=10, window_seconds=300, lockout_seconds=900)
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
        "status": current_user.status
    }
