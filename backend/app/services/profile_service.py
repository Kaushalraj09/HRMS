from typing import Optional
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.user import User
from app.schemas.profile import EmployeeProfile, ProfileUpdate
from app.utils.employee_code import normalize_employee_code

def get_employee_profile(db: Session, user_id: int) -> Optional[EmployeeProfile]:
    employee = db.query(Employee).filter(Employee.user_id == user_id).first()
    if not employee:
        return None
    
    # Get profile image from users table
    user = db.query(User).filter(User.id == user_id).first()
    profile_image = user.profile_image if user else None
    
    # Initials logic
    initials = f"{employee.first_name[0] if employee.first_name else ''}{employee.last_name[0] if employee.last_name else ''}".upper()
    
    return {
        "id": employee.id,
        "employeeId": normalize_employee_code(employee.employee_code),
        "firstName": employee.first_name,
        "lastName": employee.last_name,
        "initials": initials,
        "role": employee.designation or "Employee",
        "department": employee.department or "General",
        "shift": employee.shift_type or "General Shift",
        "status": employee.status,
        "profileImage": profile_image,
        "personalDetails": {
            "firstName": employee.first_name,
            "lastName": employee.last_name,
            "gender": employee.gender,
            "dateOfBirth": employee.dob,
            "maritalStatus": employee.marital_status,
            "bloodGroup": employee.blood_group
        },
        "contactDetails": {
            "officialEmail": employee.official_email,
            "personalEmail": employee.personal_email,
            "mobileNumber": employee.mobile,
            "alternateMobile": employee.alternate_mobile,
            "location": employee.work_location
        }
    }

def update_employee_profile(db: Session, user_id: int, payload: ProfileUpdate):
    employee = db.query(Employee).filter(Employee.user_id == user_id).first()
    if not employee:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if payload.personalDetails:
        p = payload.personalDetails
        employee.first_name = p.firstName
        employee.last_name = p.lastName
        employee.gender = p.gender
        employee.dob = p.dateOfBirth
        employee.marital_status = p.maritalStatus
        employee.blood_group = p.bloodGroup
        
        # Keep user display_name in sync!
        if user:
            user.display_name = f"{p.firstName} {p.lastName}".strip()
        
    if payload.contactDetails:
        c = payload.contactDetails
        employee.personal_email = c.personalEmail
        employee.mobile = c.mobileNumber
        employee.alternate_mobile = c.alternateMobile
        employee.work_location = c.location
        
    if payload.profileImage is not None:
        if user:
            user.profile_image = payload.profileImage
        
    db.commit()
    db.refresh(employee)
    return {"success": True, "message": "Profile updated successfully"}
