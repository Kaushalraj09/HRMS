from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate # Assumes you have this in schemas/employee.py
from app.core.security import hash_password

def create_employee(db: Session, obj_in: EmployeeCreate):
    # 1. Get the 'employee' role
    emp_role = db.query(Role).filter(Role.name == "employee").first()
    
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
        **obj_in.model_dump() # This automatically maps all Pydantic fields to SQL columns
    )
    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)
    return new_employee

def list_employees(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Employee).offset(skip).limit(limit).all()
