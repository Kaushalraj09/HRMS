from sqlalchemy import func, or_
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
    hr_code = f"EMP-{new_user.id:04d}"
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
    
    # 4. Create corresponding shadow Employee record
    name_parts = obj_in.fullName.split(" ", 1)
    first_name = name_parts[0] if obj_in.fullName else "HR"
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    shadow_emp = Employee(
        user_id=new_user.id,
        employee_code=hr_code,
        first_name=first_name,
        last_name=last_name,
        official_email=obj_in.email,
        mobile=obj_in.phone,
        department=obj_in.department,
        designation=obj_in.designation,
        employee_type="Full-Time",
        work_location="Main Office",
        shift_type="General Shift",
        status=obj_in.status
    )
    db.add(shadow_emp)
    
    db.commit()
    db.refresh(new_hr)
    return new_hr

def list_hrs(db: Session, page: int = 1, limit: int = 10, search: str = "", status: str = ""):
    hr_query = db.query(HrUser)
    
    if status:
        hr_query = hr_query.filter(HrUser.status == status)
        
    search_value = (search or "").strip()
    if search_value:
        like_val = f"%{search_value}%"
        hr_query = hr_query.filter(
            or_(
                HrUser.full_name.ilike(like_val),
                HrUser.email.ilike(like_val),
                HrUser.phone.ilike(like_val),
                HrUser.department.ilike(like_val),
                HrUser.designation.ilike(like_val)
            )
        )
        
    hr_profiles = hr_query.order_by(HrUser.id.desc()).all()
    for hr in hr_profiles:
        hr.hr_code = f"EMP-{hr.user_id:04d}"
        
    existing_user_ids = {hr.user_id for hr in hr_profiles}

    user_query = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name) == "hr")
        .filter(~User.id.in_(existing_user_ids) if existing_user_ids else True)
    )
    
    if status:
        user_query = user_query.filter(User.status == status)
        
    seeded_hr_users = user_query.order_by(User.id.desc()).all()

    fallback_profiles = []
    for user in seeded_hr_users:
        employee = db.query(Employee).filter(Employee.user_id == user.id).first()
        
        simulated = {
            "id": user.id,
            "userId": user.id,
            "hrCode": f"EMP-{user.id:04d}",
            "fullName": user.display_name,
            "email": user.email,
            "phone": employee.mobile if employee and employee.mobile else "",
            "department": employee.department if employee and employee.department else "Human Resources",
            "designation": employee.designation if employee and employee.designation else "HR",
            "status": user.status,
            "createdAt": user.created_at,
        }
        
        if search_value:
            s_lower = search_value.lower()
            matches = (
                s_lower in (simulated["fullName"] or "").lower() or
                s_lower in (simulated["email"] or "").lower() or
                s_lower in (simulated["department"] or "").lower() or
                s_lower in (simulated["designation"] or "").lower() or
                s_lower in (simulated["phone"] or "").lower() or
                s_lower in (simulated["hrCode"] or "").lower()
            )
            if not matches:
                continue
                
        fallback_profiles.append(simulated)

    combined = hr_profiles + fallback_profiles
    
    # Sort combined list by ID descending (to keep creation order)
    def get_sort_key(x):
        if isinstance(x, dict):
            return x["id"]
        return x.id

    combined.sort(key=get_sort_key, reverse=True)
    
    total = len(combined)
    start = (page - 1) * limit
    paged_data = combined[start : start + limit]
    
    return {"data": paged_data, "total": total}
