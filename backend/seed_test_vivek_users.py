"""
Script to create or update the Vivek test users across all 3 roles:
- Admin: TestVivekAdmin@gmail.com
- HR Manager: TestVivekHr@gmail.com
- Employee: TestVivekEmp@gmail.com
Password for all: Testv@1234
"""
import sys
import os
from datetime import date

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.user import User, Role
from app.models.employee import Employee
from app.models.hr_user import HrUser
from app.core.security import hash_password
from app.seeds.seed_master_data import seed_roles, seed_master_data


def seed_vivek_test_users():
    db = SessionLocal()
    try:
        # Ensure base roles exist
        seed_roles(db)
        seed_master_data(db)

        admin_role = db.query(Role).filter(Role.name == "Admin").first()
        hr_role = db.query(Role).filter(Role.name == "HR").first()
        emp_role = db.query(Role).filter(Role.name == "Employee").first()

        if not admin_role or not hr_role or not emp_role:
            print("❌ Error: Roles could not be found or seeded.")
            return

        common_password = "Testv@1234"
        hashed_pwd = hash_password(common_password)

        test_accounts = [
            {
                "email": "TestVivekAdmin@gmail.com",
                "display_name": "Vivek Admin",
                "role_id": admin_role.id,
                "role_name": "Admin",
                "profile_type": "admin",
                "dashboard": "/master-dashboard"
            },
            {
                "email": "TestVivekHr@gmail.com",
                "display_name": "Vivek HR",
                "role_id": hr_role.id,
                "role_name": "HR",
                "profile_type": "hr",
                "dashboard": "/hr-dashboard",
                "hr_data": {
                    "full_name": "Vivek HR",
                    "phone": "9876543210",
                    "department": "Human Resources",
                    "designation": "HR Manager",
                    "gender": "Male",
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
                "email": "TestVivekEmp@gmail.com",
                "display_name": "Vivek Employee",
                "role_id": emp_role.id,
                "role_name": "Employee",
                "profile_type": "employee",
                "dashboard": "/emp-dashboard",
                "employee_data": {
                    "first_name": "Vivek",
                    "last_name": "Employee",
                    "department": "Engineering",
                    "designation": "Frontend Developer",
                    "employee_type": "Full-Time",
                    "work_location": "Belagavi ICCC Office",
                    "shift_type": "General Shift",
                    "mobile": "9876543211",
                    "official_email": "TestVivekEmp@gmail.com",
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

        print("\n=== Seeding Vivek Test Users ===")
        for acc in test_accounts:
            user = db.query(User).filter(User.email.ilike(acc["email"])).first()
            if not user:
                user = User(
                    email=acc["email"],
                    password_hash=hashed_pwd,
                    display_name=acc["display_name"],
                    role_id=acc["role_id"],
                    status="Active"
                )
                db.add(user)
                db.flush()
                print(f"✅ Created User: {acc['email']} (Role: {acc['role_name']})")
            else:
                user.password_hash = hashed_pwd
                user.display_name = acc["display_name"]
                user.role_id = acc["role_id"]
                user.status = "Active"
                print(f"🔄 Updated User: {acc['email']} (Role: {acc['role_name']})")

            existing_employee = db.query(Employee).filter(Employee.user_id == user.id).first()
            existing_hr = db.query(HrUser).filter(HrUser.user_id == user.id).first()

            if acc["profile_type"] == "employee":
                emp_data = {**acc["employee_data"], "employee_code": f"{user.id:04d}"}
                if not existing_employee:
                    existing_employee = Employee(user_id=user.id, **emp_data)
                    db.add(existing_employee)
                    print(f"   ↳ Created Employee profile for {acc['email']}")
                else:
                    for field, value in emp_data.items():
                        setattr(existing_employee, field, value)
                    existing_employee.employee_code = f"{user.id:04d}"
                    existing_employee.official_email = acc["email"]
                    print(f"   ↳ Updated Employee profile for {acc['email']}")

                if existing_hr:
                    db.delete(existing_hr)

            elif acc["profile_type"] == "hr":
                hr_data = acc["hr_data"]
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
                    "official_email": acc["email"],
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
                        user_id=user.id,
                        employee_code=f"{user.id:04d}",
                        **emp_data
                    )
                    db.add(existing_employee)
                    print(f"   ↳ Created Employee record for HR user {acc['email']}")
                else:
                    for field, value in emp_data.items():
                        setattr(existing_employee, field, value)
                    existing_employee.employee_code = f"{user.id:04d}"
                    existing_employee.official_email = acc["email"]
                    print(f"   ↳ Updated Employee record for HR user {acc['email']}")

                if not existing_hr:
                    existing_hr = HrUser(user_id=user.id, hr_settings=None)
                    db.add(existing_hr)
                    print(f"   ↳ Created HrUser record for {acc['email']}")
                else:
                    print(f"   ↳ HrUser record confirmed for {acc['email']}")

            else:  # Admin
                if existing_hr:
                    db.delete(existing_hr)

        db.commit()
        print("\n🎉 All 3 test users are ready for testing!\n")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_vivekTest_users = seed_vivek_test_users()
