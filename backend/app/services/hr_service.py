from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models.employee import Employee
from app.models.user import User, Role
from app.models.hr_user import HrUser
from app.schemas.hr import HrCreate
from app.core.security import hash_password
import secrets


def _employee_to_hr_response(employee: Employee) -> dict:
    full_name = f"{employee.first_name or ''} {employee.last_name or ''}".strip()
    return {
        "id": employee.id,
        "user_id": employee.user_id,
        "hr_code": employee.employee_code,
        "full_name": full_name,
        "email": employee.official_email,
        "phone": employee.mobile,
        "department": employee.department,
        "designation": employee.designation,
        "status": employee.status,
        "created_at": employee.created_at,
    }


def create_hr(db: Session, obj_in: HrCreate):
    # Support either "HR" or "hr" naming in the roles table.
    hr_role = db.query(Role).filter(func.lower(Role.name) == "hr").first()
    if not hr_role:
        raise ValueError("HR role not found")
    
    # 1. Check if the email is already registered in the users table
    existing_user = db.query(User).filter(User.email.ilike(obj_in.email)).first()
    if existing_user:
        raise ValueError(f"An account with the email '{obj_in.email}' is already registered.")
    
    # 2. Create the User Login Account
    new_user = User(
        email=obj_in.email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        display_name=obj_in.fullName,
        role_id=hr_role.id,
        status=obj_in.status
    )
    db.add(new_user)
    db.flush() # Get the new_user.id without committing yet
    
    # 3. Create the Employee Profile (Main personnel record)
    hr_code = f"{new_user.id:04d}"
    name_parts = obj_in.fullName.split(" ", 1)
    first_name = name_parts[0] if obj_in.fullName else "HR"
    last_name = name_parts[1] if len(name_parts) > 1 else ""
    
    new_employee = Employee(
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
    db.add(new_employee)
    db.flush()
    
    # 4. Create the HR Extension record
    new_hr = HrUser(
        user_id=new_user.id,
        hr_settings=None
    )
    db.add(new_hr)
    
    db.commit()
    db.refresh(new_employee)
    # Send a one-time password setup link; credentials never leave the server.
    from app.services.auth_service import generate_reset_token
    from app.services.mail_service import send_reset_email
    from app.core.config import settings
    reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?token={generate_reset_token(new_user)}"
    send_reset_email(new_user.email, new_user.display_name, reset_link)
    return _employee_to_hr_response(new_employee)

def list_hrs(db: Session, page: int = 1, limit: int = 10, search: str = "", status: str = ""):
    # Query Employee table filtered by HR role
    query = db.query(
        Employee.id.label("id"),
        Employee.user_id.label("user_id"),
        Employee.employee_code.label("hr_code"),
        (Employee.first_name + " " + Employee.last_name).label("full_name"),
        Employee.official_email.label("email"),
        Employee.mobile.label("phone"),
        Employee.department.label("department"),
        Employee.designation.label("designation"),
        Employee.status.label("status"),
        Employee.created_at.label("created_at")
    ).join(User, Employee.user_id == User.id).join(Role, User.role_id == Role.id).filter(func.lower(Role.name) == "hr")

    if status:
        query = query.filter(Employee.status == status)
    else:
        query = query.filter(Employee.status != "Deleted")
        
    search_value = (search or "").strip()
    if search_value:
        like_val = f"%{search_value}%"
        full_name = func.coalesce(Employee.first_name, "") + " " + func.coalesce(Employee.last_name, "")
        query = query.filter(
            or_(
                Employee.first_name.ilike(like_val),
                Employee.last_name.ilike(like_val),
                full_name.ilike(like_val),
                Employee.official_email.ilike(like_val),
                Employee.mobile.ilike(like_val),
                Employee.department.ilike(like_val),
                Employee.designation.ilike(like_val)
            )
        )

    total = query.count()
    paged_records = query.order_by(Employee.id.desc()).offset((page - 1) * limit).limit(limit).all()

    paged_data = []
    for r in paged_records:
        r_dict = dict(r._mapping)
        paged_data.append(r_dict)

    return {"data": paged_data, "total": total}
