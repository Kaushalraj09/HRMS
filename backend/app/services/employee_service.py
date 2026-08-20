from sqlalchemy import literal, or_, func
from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
import secrets

from app.core.security import hash_password

from sqlalchemy.orm import joinedload

def _employee_query(db: Session):
    return (
        db.query(Employee)
        .options(joinedload(Employee.shift))
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(Employee.status != "Deleted", User.status != "Deleted")
    )

def generate_random_password(length: int = 12) -> str:
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def create_employee(db: Session, obj_in: EmployeeCreate):
    # 1. Check if the email is already registered in the users table
    existing_user = db.query(User).filter(User.email.ilike(obj_in.official_email)).first()
    if existing_user:
        raise ValueError(f"An account with the email '{obj_in.official_email}' is already registered.")

    # Support either "Employee" or "employee" naming in the roles table.
    emp_role = db.query(Role).filter(func.lower(Role.name) == "employee").first()
    if not emp_role:
        raise ValueError("Employee role not found")
    
    # 2. Create the User Login
    # Note: We use the official_email as the login email
    new_user = User(
        email=obj_in.official_email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        display_name=f"{obj_in.first_name} {obj_in.last_name}",
        role_id=emp_role.id,
        status="Active"
    )
    db.add(new_user)
    db.flush()
    
    # 3. Create the Employee Profile
    emp_code = f"{new_user.id:04d}"
    new_employee = Employee(
        user_id=new_user.id,
        employee_code=emp_code,
        **obj_in.model_dump()
    )
    db.add(new_employee)
    db.flush()

    # Send a one-time password setup link; credentials never leave the server.
    from app.services.auth_service import generate_reset_token
    from app.services.mail_service import send_reset_email
    from app.core.config import settings
    from app.services.account_access_service import InvitationDeliveryError
    reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?token={generate_reset_token(new_user)}"
    if not send_reset_email(new_user.email, new_user.display_name, reset_link):
        db.rollback()
        raise InvitationDeliveryError("Unable to deliver the password setup email. No employee account was created.")

    db.commit()
    db.refresh(new_employee)

    # Initialize standard onboarding document requirements
    try:
        from app.services.document_service import initialize_employee_requirements
        initialize_employee_requirements(db, new_employee.id)
    except Exception as e:
        # Non-blocking requirement initialization
        pass

    from app.services.dashboard_service import invalidate_dashboard_cache
    invalidate_dashboard_cache(db)
    return new_employee

def _matches_employee_filters(employee, search: str, department: str, employee_type: str, status: str) -> bool:
    if employee.status == "Deleted":
        return False
    search_value = (search or "").strip().lower()
    if search_value:
        searchable_values = [
            f"{employee.first_name or ''} {employee.last_name or ''}",
            employee.employee_code or "",
            employee.department or "",
            employee.official_email or "",
        ]
        if not any(search_value in value.lower() for value in searchable_values):
            return False

    if department and employee.department != department:
        return False
    if employee_type and employee.employee_type != employee_type:
        return False
    if status and employee.status != status:
        return False

    return True


def list_employees(
    db: Session,
    page: int = 1,
    limit: int = 10,
    search: str = "",
    department: str = "",
    employee_type: str = "",
    status: str = "",
    exclude_hr: bool = False,
):
    from sqlalchemy import Date, String, Integer

    # Query Employee table records joining User and Role
    emp_q = (
        db.query(
            Employee.id.label("id"),
            Employee.user_id.label("user_id"),
            Employee.reporting_manager_id.label("reporting_manager_id"),
            Employee.employee_code.label("employee_code"),
            Employee.first_name.label("first_name"),
            Employee.last_name.label("last_name"),
            Employee.gender.label("gender"),
            Employee.dob.label("dob"),
            Employee.marital_status.label("marital_status"),
            Employee.blood_group.label("blood_group"),
            Employee.department.label("department"),
            Employee.designation.label("designation"),
            Employee.employee_type.label("employee_type"),
            Employee.work_location.label("work_location"),
            Employee.shift_type.label("shift_type"),
            Employee.shift_id.label("shift_id"),
            Employee.doj.label("doj"),
            Employee.official_email.label("official_email"),
            Employee.personal_email.label("personal_email"),
            Employee.mobile.label("mobile"),
            Employee.alternate_mobile.label("alternate_mobile"),
            Employee.emergency_contact_name.label("emergency_contact_name"),
            Employee.emergency_contact_number.label("emergency_contact_number"),
            Employee.status.label("status"),
            Employee.created_at.label("created_at")
        )
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(
            func.lower(Role.name) != "admin",
            Employee.status != "Deleted",
            User.status != "Deleted"
        )
    )

    if exclude_hr:
        emp_q = emp_q.filter(func.lower(Role.name) != "hr")

    search_value = (search or "").strip()
    if search_value:
        like_value = f"%{search_value}%"
        full_name = func.coalesce(Employee.first_name, "") + literal(" ") + func.coalesce(Employee.last_name, "")
        emp_q = emp_q.filter(
            or_(
                Employee.first_name.ilike(like_value),
                Employee.last_name.ilike(like_value),
                full_name.ilike(like_value),
                Employee.employee_code.ilike(like_value),
                Employee.department.ilike(like_value),
                Employee.official_email.ilike(like_value),
            )
        )

    if department:
        emp_q = emp_q.filter(Employee.department == department)
    if employee_type:
        emp_q = emp_q.filter(Employee.employee_type == employee_type)
    if status:
        emp_q = emp_q.filter(Employee.status == status)

    total = emp_q.count()

    paged_records = emp_q.order_by(Employee.id.desc()).offset((page - 1) * limit).limit(limit).all()

    paged_data = []
    from app.models.master_data import Shift
    for r in paged_records:
        r_dict = dict(r._mapping)
        if r_dict.get("shift_id"):
            s_obj = db.query(Shift).filter(Shift.id == r_dict["shift_id"]).first()
            if s_obj:
                r_dict["shift"] = s_obj
        paged_data.append(r_dict)

    return {
        "data": paged_data,
        "total": total,
    }

def get_employee_by_id(db: Session, employee_id: int):
    return _employee_query(db).filter(Employee.id == employee_id).first()

def get_employee_credentials(db: Session, employee_id: int):
    if employee_id >= 10000:
        hr_id = employee_id - 10000
        hr = db.query(HrUser).filter(HrUser.id == hr_id).first()
        if not hr:
            return None
        user = db.query(User).filter(User.id == hr.user_id).first()
        if not user or user.status == "Deleted":
            return None
        emp_code = f"EMP-{hr.user_id:04d}"
        return {
            "employee_id": employee_id,
            "employee_code": emp_code,
            "employee_name": hr.full_name,
            "username": user.email,
            "email": user.email,
            "activation_required": True,
            "temporary_password_hint": "Temporary testing password: first 5 email letters + @1234. Replace with setup email after SMTP is configured.",
            "status": user.status or hr.status or "Active",
        }
        
    employee = _employee_query(db).filter(Employee.id == employee_id).first()
    if not employee:
        return None

    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user or user.status == "Deleted":
        return None

    return {
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": f"{employee.first_name} {employee.last_name}".strip(),
        "username": user.email,
        "email": user.email,
        "activation_required": True,
        "temporary_password_hint": "Temporary testing password: first 5 email letters + @1234. Replace with setup email after SMTP is configured.",
        "status": user.status or employee.status or "Active",
    }

def update_employee(db: Session, employee_id: int, payload: EmployeeUpdate):
    employee = _employee_query(db).filter(Employee.id == employee_id).first()
    if not employee:
        return None

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(employee, field, value)

    # Keep the linked login account aligned with profile changes.
    user = db.query(User).filter(User.id == employee.user_id).first()
    if user:
        if "official_email" in updates and updates["official_email"]:
            user.email = updates["official_email"]
        if "status" in updates and updates["status"]:
            user.status = updates["status"]
        first_name = updates.get("first_name", employee.first_name)
        last_name = updates.get("last_name", employee.last_name)
        user.display_name = f"{first_name} {last_name}".strip()

    db.commit()
    db.refresh(employee)

    from app.services.dashboard_service import invalidate_dashboard_cache
    invalidate_dashboard_cache(db)

    return employee

def delete_employee(db: Session, employee_id: int) -> bool:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return False
        
    employee.status = "Deleted"
    
    # Update linked User account status
    user = db.query(User).filter(User.id == employee.user_id).first()
    if user:
        user.status = "Deleted"
        
    db.commit()

    from app.services.dashboard_service import invalidate_dashboard_cache
    invalidate_dashboard_cache(db)

    return True
