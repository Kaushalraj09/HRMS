from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.core.security import hash_password

def _employee_query(db: Session):
    return (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name) == "employee")
    )

def create_employee(db: Session, obj_in: EmployeeCreate):
    # Support either "Employee" or "employee" naming in the roles table.
    emp_role = db.query(Role).filter(func.lower(Role.name) == "employee").first()
    if not emp_role:
        raise ValueError("Employee role not found")
    
    # 2. Create the User Login
    # Note: We use the official_email as the login email
    new_user = User(
        email=obj_in.official_email,
        password_hash=hash_password("Employee@123"), # Default password
        display_name=f"{obj_in.first_name} {obj_in.last_name}",
        role_id=emp_role.id,
        status="Active"
    )
    db.add(new_user)
    db.flush()
    
    # 3. Create the Employee Profile
    emp_code = f"EMP-{new_user.id:04d}"
    new_employee = Employee(
        user_id=new_user.id,
        employee_code=emp_code,
        **obj_in.model_dump()
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

def list_employees(db: Session, skip: int = 0, limit: int = 100):
    # Filter out shadow employee records of HR users so they aren't duplicated in the list
    employees = (
        db.query(Employee)
        .join(User, Employee.user_id == User.id)
        .join(Role, User.role_id == Role.id)
        .filter(func.lower(Role.name) != "hr")
        .order_by(Employee.id.desc())
        .all()
    )
    hrs = db.query(HrUser).order_by(HrUser.id.desc()).all()
    
    for hr in hrs:
        name_parts = hr.full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        emp_code = f"EMP-{hr.user_id:04d}"
        
        simulated_emp = Employee(
            id=hr.id + 10000,
            user_id=hr.user_id,
            employee_code=emp_code,
            first_name=first_name,
            last_name=last_name,
            gender="Other",
            department=hr.department or "Human Resources",
            designation=hr.designation or "HR Manager",
            employee_type="Full-Time",
            work_location="Main Office",
            shift_type="General Shift",
            official_email=hr.email,
            mobile=hr.phone or "0000000000",
            status=hr.status or "Active",
            created_at=hr.created_at
        )
        employees.append(simulated_emp)
        
    employees.sort(key=lambda e: e.id, reverse=True)
    return employees[skip : skip + limit]

def get_employee_by_id(db: Session, employee_id: int):
    if employee_id >= 10000:
        hr_id = employee_id - 10000
        hr = db.query(HrUser).filter(HrUser.id == hr_id).first()
        if not hr:
            return None
        name_parts = hr.full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        emp_code = f"EMP-{hr.user_id:04d}"
        return Employee(
            id=hr.id + 10000,
            user_id=hr.user_id,
            employee_code=emp_code,
            first_name=first_name,
            last_name=last_name,
            gender="Other",
            department=hr.department or "Human Resources",
            designation=hr.designation or "HR Manager",
            employee_type="Full-Time",
            work_location="Main Office",
            shift_type="General Shift",
            official_email=hr.email,
            mobile=hr.phone or "0000000000",
            status=hr.status or "Active",
            created_at=hr.created_at
        )
    return _employee_query(db).filter(Employee.id == employee_id).first()

def get_employee_credentials(db: Session, employee_id: int):
    if employee_id >= 10000:
        hr_id = employee_id - 10000
        hr = db.query(HrUser).filter(HrUser.id == hr_id).first()
        if not hr:
            return None
        user = db.query(User).filter(User.id == hr.user_id).first()
        if not user:
            return None
        emp_code = f"EMP-{hr.user_id:04d}"
        return {
            "employee_id": employee_id,
            "employee_code": emp_code,
            "employee_name": hr.full_name,
            "username": user.email,
            "email": user.email,
            "password": "hr1234" if user.email == "hr@hrms.com" else "Employee@123",
            "temporary_password_hint": "Default temporary password for HR user.",
            "status": user.status or hr.status or "Active",
        }
        
    employee = _employee_query(db).filter(Employee.id == employee_id).first()
    if not employee:
        return None

    user = db.query(User).filter(User.id == employee.user_id).first()
    if not user:
        return None

    default_password = "emp123" if user.email == "emp@hrms.com" else "Employee@123"
    return {
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "employee_name": f"{employee.first_name} {employee.last_name}".strip(),
        "username": user.email,
        "email": user.email,
        "password": default_password,
        "temporary_password_hint": "Default temporary password. Ask the employee to change it after first login.",
        "status": user.status or employee.status or "Active",
    }

def update_employee(db: Session, employee_id: int, payload: EmployeeUpdate):
    if employee_id >= 10000:
        hr_id = employee_id - 10000
        hr = db.query(HrUser).filter(HrUser.id == hr_id).first()
        if not hr:
            return None
        updates = payload.model_dump(exclude_unset=True)
        if "first_name" in updates or "last_name" in updates:
            first_name = updates.get("first_name", hr.full_name.split(" ", 1)[0])
            last_name = updates.get("last_name", hr.full_name.split(" ", 1)[1] if " " in hr.full_name else "")
            hr.full_name = f"{first_name} {last_name}".strip()
        if "department" in updates:
            hr.department = updates["department"]
        if "designation" in updates:
            hr.designation = updates["designation"]
        if "official_email" in updates:
            hr.email = updates["official_email"]
        if "mobile" in updates:
            hr.phone = updates["mobile"]
        if "status" in updates:
            hr.status = updates["status"]
            
        user = db.query(User).filter(User.id == hr.user_id).first()
        if user:
            if "official_email" in updates:
                user.email = updates["official_email"]
            if "status" in updates:
                user.status = updates["status"]
            user.display_name = hr.full_name
            
        db.commit()
        db.refresh(hr)
        
        name_parts = hr.full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        emp_code = f"EMP-{hr.user_id:04d}"
        return Employee(
            id=hr.id + 10000,
            user_id=hr.user_id,
            employee_code=emp_code,
            first_name=first_name,
            last_name=last_name,
            gender="Other",
            department=hr.department or "Human Resources",
            designation=hr.designation or "HR Manager",
            employee_type="Full-Time",
            work_location="Main Office",
            shift_type="General Shift",
            official_email=hr.email,
            mobile=hr.phone or "0000000000",
            status=hr.status or "Active",
            created_at=hr.created_at
        )

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
        first_name = updates.get("first_name", employee.first_name)
        last_name = updates.get("last_name", employee.last_name)
        user.display_name = f"{first_name} {last_name}".strip()

    db.commit()
    db.refresh(employee)
    return employee
