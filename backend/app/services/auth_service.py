from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import verify_password, create_access_token
from app.schemas.auth import LoginRequest, LoginResponse

def authenticate_user(db: Session, request: LoginRequest):
    # 1. Look for user in DB
    user = db.query(User).filter(User.email == request.email).first()
    
    # 2. If user exists and password is correct
    if user and verify_password(request.password, user.password_hash):
        # 3. Create a token
        token = create_access_token(subject=user.email)
        
        # 4. Format the response
        return {
            "accessToken": token,
            "me": {
                "id": user.id,
                "email": user.email,
                "displayName": user.display_name,
                "role": user.role.name, # Accesses the relationship from Lesson 2
                "status": user.status
            }
        }
    
    return None # If login failed
