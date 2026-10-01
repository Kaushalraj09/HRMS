from sqlalchemy import literal, or_, func
from sqlalchemy.orm import Session, joinedload
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
import secrets
import string

from app.core.security import hash_password

def _employee_query(db: Session):
    return (
        db.query(Employee)
        .options(joinedload(Employee.shift))
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(Employee.status != "Deleted", User.status != "Deleted")
    )

def generate_random_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def create_employee(db: Session, obj_in: EmployeeCreate):
    # 1. Check if the email is already registered in the users table
    existing_user = db.query(User).filter(User.email.ilike(obj_in.official_email)).first()
    if existing_user:
        raise ValueError(f"An account with the email '{obj_in.official_email}' is already registered.")

    # Determine target role (defaults to employee, supports manager)
    target_role_name = (obj_in.role or "employee").lower().strip()
    user_role = db.query(Role).filter(func.lower(Role.name) == target_role_name).first()
    if not user_role:
        user_role = db.query(Role).filter(func.lower(Role.name) == "employee").first()
    if not user_role:
        raise ValueError("Employee role not found")
    
    first_name = (obj_in.first_name or "").strip()
    last_name = (obj_in.last_name or "").strip()
    official_email = obj_in.official_email.strip()

    from app.services.account_access_service import build_temporary_testing_password, apply_temporary_testing_password
    initial_password = build_temporary_testing_password(official_email)

    # 2. Create the User Login
    # Note: We use the official_email as the login email
    new_user = User(
        email=official_email,
        password_hash=hash_password(initial_password),
        display_name=f"{first_name} {last_name}".strip(),
        role_id=user_role.id,
        status="Active"
    )
    db.add(new_user)
    db.flush()
    
    # 3. Create the Employee Profile using atomic sequential AIVAN code or custom code
    from app.services.employee_code_service import allocate_next_employee_code, record_code_history
    from app.utils.employee_code import normalize_employee_code

    custom_code = getattr(obj_in, "employee_code", None)
    if custom_code and custom_code.strip() and custom_code.strip().upper() not in ["AUTO", "NEW"]:
        emp_code = normalize_employee_code(custom_code)
        existing = db.query(Employee).filter(Employee.employee_code == emp_code).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Employee code '{emp_code}' is already in use.")
        reason = "Initial custom assignment"
    else:
        emp_code = allocate_next_employee_code(db, "AIVAN")
        reason = "Initial sequential assignment"

    if getattr(obj_in, "reporting_manager_id", None):
        mgr = db.query(Employee).filter(Employee.id == obj_in.reporting_manager_id, Employee.status != "Deleted").first()
        if not mgr:
            raise ValueError("Selected reporting manager does not exist or has been deleted.")

    dump_dict = obj_in.model_dump()
    dump_dict.pop("role", None)
    dump_dict.pop("employee_code", None)
    dump_dict["first_name"] = first_name
    dump_dict["last_name"] = last_name
    dump_dict["official_email"] = official_email
    new_employee = Employee(
        user_id=new_user.id,
        employee_code=emp_code,
        **dump_dict
    )
    db.add(new_employee)
    db.flush()

    record_code_history(
        db=db,
        employee_id=new_employee.id,
        old_code=None,
        new_code=emp_code,
        reason=reason,
        changed_by="SYSTEM",
    )

    # Send a one-time password setup link; credentials never leave the server.
    from app.services.auth_service import generate_reset_token
    from app.services.mail_service import send_reset_email
    from app.core.config import settings
    reset_link = f"{settings.FRONTEND_URL.rstrip('/')}/auth/reset-password?token={generate_reset_token(new_user)}"
    try:
        email_sent = send_reset_email(new_user.email, new_user.display_name, reset_link)
        if not email_sent:
            apply_temporary_testing_password(db, new_user)
    except Exception as exc:
        apply_temporary_testing_password(db, new_user)

    db.commit()
    db.refresh(new_employee)

    # Initialize standard onboarding document requirements
    try:
        from app.services.document_service import initialize_employee_requirements
        initialize_employee_requirements(db, new_employee.id)
    except Exception:
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
            getattr(employee, "legacy_employee_code", None) or "",
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
    # Query Employee table records joining User and Role
    emp_q = (
        db.query(
            Employee.id.label("id"),
            Employee.user_id.label("user_id"),
            Employee.reporting_manager_id.label("reporting_manager_id"),
            Employee.employee_code.label("employee_code"),
            Employee.legacy_employee_code.label("legacy_employee_code"),
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
                Employee.legacy_employee_code.ilike(like_value),
                Employee.department.ilike(like_value),
                Employee.official_email.ilike(like_value),
            )
        )

    if department:
        emp_q = emp_q.filter(Employee.department == department)
    if employee_type:
        emp_q = emp_q.filter(Employee.employee_type == employee_type)
    if status:
        status_lower = status.strip().lower()
        if status_lower == "inactive":
            emp_q = emp_q.filter(or_(Employee.status == "Inactive", Employee.status == "Deleted"))
        elif status_lower == "all":
            emp_q = emp_q.filter(Employee.status != "Deleted")
        else:
            emp_q = emp_q.filter(Employee.status == status)
    else:
        emp_q = emp_q.filter(Employee.status == "Active")

    total = emp_q.count()

    paged_records = emp_q.order_by(Employee.id.desc()).offset((page - 1) * limit).limit(limit).all()

    paged_data = []
    from app.models.master_data import Shift
    for r in paged_records:
        r_dict = dict(r._mapping)
        r_dict["employee_id"] = r_dict["id"]
        if r_dict.get("shift_id"):
            s_obj = db.query(Shift).filter(Shift.id == r_dict["shift_id"]).first()
            if s_obj:
                r_dict["shift"] = s_obj
        paged_data.append(r_dict)

    # Calculate organization-wide / department stats
    stats_base_q = (
        db.query(Employee.id, Employee.status)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(
            func.lower(Role.name) != "admin",
            Employee.status != "Deleted",
            User.status != "Deleted"
        )
    )
    if exclude_hr:
        stats_base_q = stats_base_q.filter(func.lower(Role.name) != "hr")
    if department:
        stats_base_q = stats_base_q.filter(Employee.department == department)

    all_stat_records = stats_base_q.all()
    total_stat = len(all_stat_records)
    active_stat = sum(1 for r in all_stat_records if (r.status or "").strip().lower() == "active")
    inactive_stat = sum(1 for r in all_stat_records if (r.status or "").strip().lower() in ["inactive", "deleted"])

    from app.models.timeoff import TimeOffRequest
    from datetime import date
    today_date = date.today()
    on_leave_emp_ids = set(
        row[0] for row in db.query(TimeOffRequest.employee_id).filter(
            TimeOffRequest.date == today_date,
            TimeOffRequest.status.in_(["Approved", "Active", "Completed"])
        ).all()
    )
    on_leave_stat = sum(
        1 for r in all_stat_records
        if (r.status or "").strip().lower() in ["on leave", "leave"] or r.id in on_leave_emp_ids
    )

    stats_summary = {
        "total": total_stat,
        "active": active_stat,
        "on_leave": on_leave_stat,
        "inactive": inactive_stat,
    }

    return {
        "data": paged_data,
        "total": total,
        "stats": stats_summary,
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
    role_to_set = updates.pop("role", None)
    for field, value in updates.items():
        setattr(employee, field, value)

    # Keep the linked login account aligned with profile changes.
    user = db.query(User).filter(User.id == employee.user_id).first()
    if user:
        if role_to_set:
            role_rec = db.query(Role).filter(func.lower(Role.name) == role_to_set.lower().strip()).first()
            if role_rec:
                user.role_id = role_rec.id
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
        
    # Soft deletion: Mark as Inactive so profile/data is preserved but excluded from active workforce metrics
    employee.status = "Inactive"
    
    # Disable linked User account login
    user = db.query(User).filter(User.id == employee.user_id).first()
    if user:
        user.status = "Inactive"
        
    db.commit()

    from app.services.dashboard_service import invalidate_dashboard_cache
    invalidate_dashboard_cache(db)
    return True


def assign_manager_role(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Employee not found")

    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user:
        raise ValueError("User account not found for employee")

    manager_role = db.query(Role).filter(func.lower(Role.name) == "manager").first()
    if not manager_role:
        manager_role = Role(name="Manager")
        db.add(manager_role)
        db.flush()

    user.role_id = manager_role.id
    db.commit()
    db.refresh(employee)
    return employee


def revoke_manager_role(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise ValueError("Employee not found")

    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user:
        raise ValueError("User account not found for employee")

    emp_role = db.query(Role).filter(func.lower(Role.name) == "employee").first()
    if not emp_role:
        raise ValueError("Employee role not found")

    user.role_id = emp_role.id
    db.commit()
    db.refresh(employee)
    return employee


def get_all_managers(db: Session) -> list[Employee]:
    manager_role = db.query(Role).filter(func.lower(Role.name) == "manager").first()
    if not manager_role:
        return []
    managers = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .filter(User.role_id == manager_role.id, Employee.status != "Deleted")
        .order_by(Employee.first_name, Employee.last_name)
        .all()
    )
    for m in managers:
        m.direct_reports_count = (
            db.query(Employee)
            .filter(Employee.reporting_manager_id == m.id, Employee.status != "Deleted")
            .count()
        )
    return managers


def assign_team_to_manager(db: Session, manager_employee_id: int, employee_ids: list[int]) -> list[Employee]:
    manager = db.query(Employee).filter(Employee.id == manager_employee_id).first()
    if not manager:
        raise ValueError("Manager employee not found")

    # Unassign existing employees under this manager who are not in the new list
    existing_team = db.query(Employee).filter(Employee.reporting_manager_id == manager_employee_id).all()
    for emp in existing_team:
        if emp.id not in employee_ids:
            emp.reporting_manager_id = None

    # Assign new employees under this manager (prevent self-reporting)
    for emp_id in employee_ids:
        if emp_id == manager_employee_id:
            continue
        emp = db.query(Employee).filter(Employee.id == emp_id).first()
        if emp:
            emp.reporting_manager_id = manager_employee_id

    db.commit()
    return db.query(Employee).filter(Employee.reporting_manager_id == manager_employee_id).all()


def get_manager_team(db: Session, manager_employee_id: int) -> list[Employee]:
    return (
        db.query(Employee)
        .filter(Employee.reporting_manager_id == manager_employee_id, Employee.status != "Deleted")
        .order_by(Employee.first_name, Employee.last_name)
        .all()
    )
