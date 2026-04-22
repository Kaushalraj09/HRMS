from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.employee import Employee
from app.core.security import hash_password
from datetime import date

def seed_users(db: Session):
    # Get roles
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    hr_role = db.query(Role).filter(Role.name == "HR").first()
    emp_role = db.query(Role).filter(Role.name == "Employee").first()

    if not admin_role or not hr_role or not emp_role:
        print("Roles not found. Please seed roles first.")
        return

    demo_users = [
        {
            "email": "admin@hrms.com",
            "password": "admin123",
            "display_name": "System Admin",
            "role_id": admin_role.id,
            "employee_data": {
                "employee_code": "EMP001",
                "first_name": "System",
                "last_name": "Admin",
                "mobile": "9876543210",
                "official_email": "admin@hrms.com",
                "doj": date(2024, 1, 1)
            }
        },
        {
            "email": "hr@hrms.com",
            "password": "hr1234",
            "display_name": "HR Manager",
            "role_id": hr_role.id,
            "employee_data": {
                "employee_code": "EMP002",
                "first_name": "HR",
                "last_name": "Manager",
                "mobile": "9876543211",
                "official_email": "hr@hrms.com",
                "doj": date(2024, 1, 15)
            }
        },
        {
            "email": "emp@hrms.com",
            "password": "emp123",
            "display_name": "Kaushal",
            "role_id": emp_role.id,
            "employee_data": {
                "employee_code": "EMP003",
                "first_name": "John",
                "last_name": "Employee",
                "mobile": "9876543212",
                "official_email": "emp@hrms.com",
                "doj": date(2024, 2, 1)
            }
        }
    ]

    for user_info in demo_users:
        existing_user = db.query(User).filter(User.email == user_info["email"]).first()
        if not existing_user:
            # Create User
            new_user = User(
                email=user_info["email"],
                password_hash=hash_password(user_info["password"]),
                display_name=user_info["display_name"],
                role_id=user_info["role_id"]
            )
            db.add(new_user)
            db.flush() # Get the user id

            # Create Employee Profile
            emp_data = user_info["employee_data"]
            new_employee = Employee(
                user_id=new_user.id,
                **emp_data
            )
            db.add(new_employee)
            print(f"Added demo user and profile: {user_info['email']}")
        else:
            print(f"User {user_info['email']} already exists")
    
    db.commit()
