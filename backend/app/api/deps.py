from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
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
    token = token or request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not token:
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        active_dashboard: str = payload.get("activeDashboard")
        token_version = payload.get("tv")
        if email is None or payload.get("type") != "access":
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
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
