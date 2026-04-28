from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.user import User, Role
from app.models.hr_user import HrUser
from app.schemas.hr import HrCreate
from app.core.security import hash_password

def create_hr(db: Session, obj_in: HrCreate):
    # Support either "HR" or "hr" naming in the roles table.
    hr_role = db.query(Role).filter(func.lower(Role.name) == "hr").first()
    if not hr_role:
        raise ValueError("HR role not found")
    
    # 2. Create the User Login Account
    new_user = User(
        email=obj_in.email,
        password_hash=hash_password(obj_in.temporaryPassword),
        display_name=obj_in.fullName,
        role_id=hr_role.id,
        status=obj_in.status
    )
    db.add(new_user)
    db.flush() # Get the new_user.id without committing yet
    
    # 3. Create the HR Profile
    hr_code = f"HR-{new_user.id:03d}" # Simple auto-code: HR-001, HR-002
    new_hr = HrUser(
        user_id=new_user.id,
        hr_code=hr_code,
        full_name=obj_in.fullName,
        email=obj_in.email,
        phone=obj_in.phone,
        department=obj_in.department,
        designation=obj_in.designation,
        status=obj_in.status
    )
    db.add(new_hr)
    db.commit()
    db.refresh(new_hr)
    return new_hr

def list_hrs(db: Session, skip: int = 0, limit: int = 100):
    hr_profiles = db.query(HrUser).order_by(HrUser.id.desc()).all()
    existing_user_ids = {hr.user_id for hr in hr_profiles}

    seeded_hr_users = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name) == "hr")
        .filter(~User.id.in_(existing_user_ids) if existing_user_ids else True)
        .order_by(User.id.desc())
        .all()
    )

    fallback_profiles = []
    for user in seeded_hr_users:
        employee = db.query(Employee).filter(Employee.user_id == user.id).first()
        fallback_profiles.append(
            {
                "id": user.id,
                "userId": user.id,
                "hrCode": f"HR-{user.id:03d}",
                "fullName": user.display_name,
                "email": user.email,
                "phone": employee.mobile if employee and employee.mobile else "",
                "department": employee.department if employee and employee.department else "Human Resources",
                "designation": employee.designation if employee and employee.designation else "HR",
                "status": user.status,
                "createdAt": user.created_at,
            }
        )

    combined = hr_profiles + fallback_profiles
    return combined[skip: skip + limit]
