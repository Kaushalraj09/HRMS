from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

# This tells passlib to use "bcrypt" for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None, additional_claims: dict = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {"exp": expire, "sub": str(subject), "type": "access"}
    if additional_claims:
        to_encode.update(additional_claims)
    # Token types must not be overridden by callers. This keeps short-lived
    # WebSocket tickets from being accepted as regular API credentials.
    to_encode["type"] = "access"
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_websocket_ticket(subject: Union[str, Any], user_id: int) -> str:
    """Create a short-lived ticket solely for a WebSocket handshake."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=1)
    payload = {
        "exp": expire,
        "sub": str(subject),
        "uid": user_id,
        "type": "websocket",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
