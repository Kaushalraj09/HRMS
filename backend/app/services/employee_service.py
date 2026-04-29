from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.core.security import hash_password

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
    return db.query(Employee).order_by(Employee.id.desc()).offset(skip).limit(limit).all()

def get_employee_by_id(db: Session, employee_id: int):
    return db.query(Employee).filter(Employee.id == employee_id).first()

def update_employee(db: Session, employee_id: int, payload: EmployeeUpdate):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
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
