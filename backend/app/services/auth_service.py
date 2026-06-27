import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest

def authenticate_user(db: Session, request: LoginRequest):
    # 1. Look for user in DB
    user = db.query(User).filter(User.email.ilike(request.email)).first()
    
    # 2. If user exists and password is correct
    if user and verify_password(request.password, user.password_hash):
        role_name = user.role.name.lower() if user.role else ""
        
        # Ensure shadow employee profile exists for HR and Admin users dynamically
        if role_name in ["hr", "admin"]:
            employee = db.query(Employee).filter(Employee.user_id == user.id).first()
            if not employee:
                fullName = user.display_name
                email = user.email
                phone = "0000000000"
                dept = "Human Resources" if role_name == "hr" else "Administration"
                desig = "HR Manager" if role_name == "hr" else "System Admin"
                
                parts = fullName.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
                
                employee = Employee(
                    user_id=user.id,
                    employee_code=f"{user.id:04d}",
                    first_name=first_name,
                    last_name=last_name,
                    official_email=email,
                    mobile=phone,
                    department=dept,
                    designation=desig,
                    employee_type="Full-Time",
                    work_location="Main Office",
                    shift_type="General Shift",
                    status="Active"
                )
                db.add(employee)
                db.commit()

        # Handle HR role selection step
        if role_name == "hr" and not request.activeDashboard:
            return {
                "requiresDashboardSelection": True,
                "availableDashboards": ["HR", "EMPLOYEE"],
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "displayName": user.display_name,
                    "role": user.role.name,
                    "status": user.status,
                    "accessibleDashboards": ["HR", "EMPLOYEE"],
                    "activeDashboard": None,
                    "profileImage": user.profile_image
                }
            }

        # Resolve active dashboard
        if role_name == "admin":
            active_dashboard = "MASTER"
        elif role_name == "hr":
            # HR selected active dashboard (should be HR or EMPLOYEE)
            active_dashboard = request.activeDashboard if request.activeDashboard in ["HR", "EMPLOYEE"] else "HR"
        else:
            active_dashboard = "EMPLOYEE"

        # 3. Create a token with the activeDashboard claim
        token = create_access_token(
            subject=user.email,
            additional_claims={"activeDashboard": active_dashboard}
        )
        
        return {
            "accessToken": token,
            "me": {
                "id": user.id,
                "email": user.email,
                "displayName": user.display_name,
                "role": user.role.name, # Accesses the relationship from Lesson 2
                "status": user.status,
                "accessibleDashboards": user.accessibleDashboards,
                "activeDashboard": active_dashboard,
                "profileImage": user.profile_image
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

def generate_reset_token(user: User) -> str:
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode = {
        "exp": expire,
        "sub": user.email,
        "type": "reset"
    }
    secret = settings.SECRET_KEY + user.password_hash
    token = jwt.encode(to_encode, secret, algorithm=settings.ALGORITHM)
    return token

def forgot_password(db: Session, request):
    user = db.query(User).filter(User.email.ilike(request.email)).first()
    if not user:
        return None
    
    from app.core.config import settings
    token = generate_reset_token(user)
    frontend_url = settings.FRONTEND_URL.rstrip("/")
    reset_link = f"{frontend_url}/auth/reset-password?token={token}"
    
    # Trigger real SMTP email send
    from app.services.mail_service import send_reset_email
    email_sent = send_reset_email(user.email, user.display_name, reset_link)

    if settings.EXPOSE_RESET_LINK_IN_RESPONSE:
        logger.info(
            "Password reset requested for %s | Reset link: %s | SMTP email dispatched: %s",
            user.email,
            reset_link,
            "YES" if email_sent else "NO"
        )
    else:
        logger.info(
            "Password reset requested for %s | SMTP email dispatched: %s",
            user.email,
            "YES" if email_sent else "NO"
        )
    
    return reset_link

def reset_password(db: Session, request):
    from jose import jwt, JWTError
    from app.core.config import settings
    if request.newPassword != request.confirmPassword:
        return {"success": False, "message": "Passwords do not match"}
    
    try:
        unverified = jwt.decode(request.token, "", options={"verify_signature": False})
        email = unverified.get("sub")
        token_type = unverified.get("type")
        if not email or token_type != "reset":
            return {"success": False, "message": "Invalid token"}
    except JWTError:
        return {"success": False, "message": "Invalid or expired token"}
    
    user = db.query(User).filter(User.email.ilike(email)).first()
    if not user:
        return {"success": False, "message": "User not found"}
    
    secret = settings.SECRET_KEY + user.password_hash
    try:
        jwt.decode(request.token, secret, algorithms=[settings.ALGORITHM])
    except JWTError:
        return {"success": False, "message": "Invalid or expired token"}
    
    user.password_hash = hash_password(request.newPassword)
    db.commit()
    
    return {"success": True, "message": "Password reset successfully"}

