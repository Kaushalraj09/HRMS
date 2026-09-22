from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.core.security import hash_password
from datetime import date
import os
import secrets


def _demo_password(env_name: str, default: str = "Testv@1234") -> str:
    return os.getenv(env_name) or default

def seed_users(db: Session):
    # Get roles
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    hr_role = db.query(Role).filter(Role.name == "HR").first()
    emp_role = db.query(Role).filter(Role.name == "Employee").first()

    if not admin_role or not hr_role or not emp_role:
        print("Roles not found. Please seed roles first.")
        return

    admin_email = os.getenv("DEMO_ADMIN_EMAIL", "TestVivekAdmin@gmail.com")
    hr_email = os.getenv("DEMO_HR_EMAIL", "TestVivekHr@gmail.com")
    emp_email = os.getenv("DEMO_EMPLOYEE_EMAIL", "TestVivekEmp@gmail.com")

    demo_users = [
        {
            "email": admin_email,
            "password": _demo_password("DEMO_ADMIN_PASSWORD"),
            "display_name": "Vivek Admin",
            "role_id": admin_role.id,
            "profile_type": "admin"
        },
        {
            "email": hr_email,
            "password": _demo_password("DEMO_HR_PASSWORD"),
            "display_name": "Vivek HR",
            "role_id": hr_role.id,
            "profile_type": "hr",
            "hr_data": {
                "full_name": "Vivek HR",
                "phone": "9876543211",
                "department": "Human Resources",
                "designation": "HR Manager",
                "gender": "Female",
                "dob": date(1992, 5, 14),
                "doj": date(2023, 1, 10),
                "bank_name": "HDFC Bank",
                "bank_account_no": "50100439281726",
                "ifsc_code": "HDFC0001234",
                "micr_code": "560240012",
                "pan_number": "ABCDE1234F",
                "pf_number": "KN/BLG/0045678/000/0000002",
                "uan_number": "100987654321"
            }
        },
        {
            "email": emp_email,
            "password": _demo_password("DEMO_EMPLOYEE_PASSWORD"),
            "display_name": "Vivek Employee",
            "role_id": emp_role.id,
            "profile_type": "employee",
            "employee_data": {
                "first_name": "Vivek",
                "last_name": "Employee",
                "department": "Engineering",
                "designation": "Frontend Developer",
                "employee_type": "Full-Time",
                "work_location": "Belagavi ICCC Office",
                "shift_type": "General Shift",
                "mobile": "9876543212",
                "official_email": emp_email,
                "gender": "Male",
                "dob": date(1996, 8, 22),
                "doj": date(2024, 2, 1),
                "bank_name": "State Bank of India",
                "bank_account_no": "30894726154",
                "ifsc_code": "SBIN0004567",
                "micr_code": "560002015",
                "pan_number": "FGHIJ5678K",
                "pf_number": "KN/BLG/0045678/000/0000003",
                "uan_number": "100123456789"
            }
        }
    ]

    for user_info in demo_users:
        existing_user = db.query(User).filter(User.email == user_info["email"]).first()
        if not existing_user:
            existing_user = User(
                email=user_info["email"],
                password_hash=hash_password(user_info["password"]),
                display_name=user_info["display_name"],
                role_id=user_info["role_id"],
                status="Active"
            )
            db.add(existing_user)
            db.flush()
        else:
            # Keep demo credentials predictable in local/dev environments.
            existing_user.password_hash = hash_password(user_info["password"])
            existing_user.display_name = user_info["display_name"]
            existing_user.role_id = user_info["role_id"]
            existing_user.status = "Active"

        existing_employee = db.query(Employee).filter(Employee.user_id == existing_user.id).first()
        existing_hr = db.query(HrUser).filter(HrUser.user_id == existing_user.id).first()

        if user_info["profile_type"] == "employee":
            emp_data = {**user_info["employee_data"], "employee_code": f"{existing_user.id:04d}"}
            if not existing_employee:
                existing_employee = Employee(user_id=existing_user.id, **emp_data)
                db.add(existing_employee)
                print(f"Added demo employee profile: {user_info['email']}")
            else:
                for field, value in emp_data.items():
                    setattr(existing_employee, field, value)
                existing_employee.employee_code = f"{existing_user.id:04d}"
                existing_employee.official_email = user_info["email"]
                existing_employee.mobile = emp_data["mobile"]
                print(f"Updated demo employee profile: {user_info['email']}")

            if existing_hr:
                db.delete(existing_hr)
        elif user_info["profile_type"] == "hr":
            hr_data = user_info["hr_data"]
            
            name_parts = hr_data["full_name"].split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""
            
            emp_data = {
                "first_name": first_name,
                "last_name": last_name,
                "department": hr_data["department"],
                "designation": hr_data["designation"],
                "employee_type": "Full-Time",
                "work_location": "Belagavi ICCC Office",
                "shift_type": "General Shift",
                "mobile": hr_data["phone"],
                "official_email": user_info["email"],
                "status": "Active",
                "gender": hr_data.get("gender"),
                "dob": hr_data.get("dob"),
                "doj": hr_data.get("doj"),
                "bank_name": hr_data.get("bank_name"),
                "bank_account_no": hr_data.get("bank_account_no"),
                "ifsc_code": hr_data.get("ifsc_code"),
                "micr_code": hr_data.get("micr_code"),
                "pan_number": hr_data.get("pan_number"),
                "pf_number": hr_data.get("pf_number"),
                "uan_number": hr_data.get("uan_number"),
            }
            if not existing_employee:
                existing_employee = Employee(
                    user_id=existing_user.id,
                    employee_code=f"{existing_user.id:04d}",
                    **emp_data
                )
                db.add(existing_employee)
            else:
                for field, value in emp_data.items():
                    setattr(existing_employee, field, value)
                existing_employee.employee_code = f"{existing_user.id:04d}"
                existing_employee.official_email = user_info["email"]

            if not existing_hr:
                existing_hr = HrUser(
                    user_id=existing_user.id,
                    hr_settings=None
                )
                db.add(existing_hr)
                print(f"Added demo HR profile: {user_info['email']}")
            else:
                # Keep it simple, no columns to update other than ensuring it exists
                print(f"Verified demo HR profile: {user_info['email']}")
        else: # admin
            if existing_hr:
                db.delete(existing_hr)
    
    db.commit()
