from sqlalchemy.orm import Session
from app.models.user import User
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.auth import LoginRequest, LoginResponse, ChangePasswordRequest

def authenticate_user(db: Session, request: LoginRequest):
    # 1. Look for user in DB
    user = db.query(User).filter(User.email == request.email).first()
    
    # 2. If user exists and password is correct
    if user and verify_password(request.password, user.password_hash):
        role_name = user.role.name.lower() if user.role else ""
        
        # Ensure shadow employee profile exists for HR user dynamically
        if role_name == "hr":
            employee = db.query(Employee).filter(Employee.user_id == user.id).first()
            if not employee:
                hr = db.query(HrUser).filter(HrUser.user_id == user.id).first()
                fullName = hr.full_name if hr else user.display_name
                email = hr.email if hr else user.email
                phone = hr.phone if hr else "0000000000"
                dept = hr.department if hr else "Human Resources"
                desig = hr.designation if hr else "HR"
                
                parts = fullName.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
                
                employee = Employee(
                    user_id=user.id,
                    employee_code=f"EMP-{user.id:04d}",
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
                    "activeDashboard": None
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
        
        # 4. Format the response
        return {
            "accessToken": token,
            "me": {
                "id": user.id,
                "email": user.email,
                "displayName": user.display_name,
                "role": user.role.name, # Accesses the relationship from Lesson 2
                "status": user.status,
                "accessibleDashboards": user.accessibleDashboards,
                "activeDashboard": active_dashboard
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

