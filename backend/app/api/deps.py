from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    auth_header_token = token
    token = auth_header_token or request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise credentials_exception

    # Explicit CSRF protection: If authenticated via cookie alone on state-changing methods
    if not auth_header_token and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        allowed_origins = {o.rstrip("/") for o in settings.BACKEND_CORS_ORIGINS if o}
        if settings.FRONTEND_URL:
            allowed_origins.add(settings.FRONTEND_URL.rstrip("/"))

        req_origin = None
        if origin:
            req_origin = origin.rstrip("/")
        elif referer:
            from urllib.parse import urlparse
            parsed = urlparse(referer)
            req_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")

        has_custom_header = bool(
            request.headers.get("x-requested-with") or
            request.headers.get("x-csrf-token")
        )
        is_valid_origin = req_origin and (req_origin in allowed_origins or "*" in allowed_origins)

        if not is_valid_origin and not has_custom_header:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed: Request origin not permitted for cookie authentication.",
            )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        active_dashboard: str = payload.get("activeDashboard")
        token_version = payload.get("tv")
        if email is None or payload.get("type") != "access":
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
        
    user = db.query(User).options(joinedload(User.role)).filter(User.email == email).first()
    if user is None or user.status in ["Inactive", "Deleted"]:
        raise credentials_exception

    # Enforce token version matching for immediate revocation on logout / password reset
    if token_version is not None and user.token_version is not None:
        if token_version != user.token_version:
            raise credentials_exception
    
    # Dynamically set the active dashboard on the user object
    user.active_dashboard = active_dashboard
    return user


def get_ws_user(db: Session, ticket: str | None) -> User | None:
    if not ticket:
        return None
    try:
        payload = jwt.decode(ticket, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id = payload.get("uid")
        if email is None or payload.get("type") != "websocket" or not isinstance(user_id, int):
            return None
        user = db.query(User).filter(User.email == email).first()
        if user is None or user.id != user_id or user.status in ["Inactive", "Deleted"]:
            return None
        return user
    except jwt.InvalidTokenError:
        return None
