from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest

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

def change_user_password(db: Session, user_id: int, request: ChangePasswordRequest):
    # 1. Basic validation
    if request.newPassword != request.confirmPassword:
        return {"success": False, "message": "New passwords do not match"}

    # 2. Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": "User not found"}

    # 3. Verify current password
    if not verify_password(request.currentPassword, user.password_hash):
        return {"success": False, "message": "Current password is incorrect"}

    # 4. Save new password
    user.password_hash = hash_password(request.newPassword)
    db.commit()
    
    return {"success": True, "message": "Password updated successfully"}

