from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.hr_user import HrUser
from app.schemas.hr import HrCreate
from app.core.security import hash_password

def create_hr(db: Session, obj_in: HrCreate):
    # 1. Get the 'hr' role ID
    hr_role = db.query(Role).filter(Role.name == "hr").first()
    
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
    return db.query(HrUser).offset(skip).limit(limit).all()
