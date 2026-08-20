from sqlalchemy.orm import Session
from app.models.user import Role
from app.models.master_data import Department, Designation, Shift, WorkLocation, LeaveType, Holiday
from datetime import date

def seed_roles(db: Session):
    roles = ["Admin", "HR", "Employee"]
    for role_name in roles:
        existing_role = db.query(Role).filter(Role.name == role_name).first()
        if not existing_role:
            new_role = Role(name=role_name)
            db.add(new_role)
            print(f"Added role: {role_name}")
        else:
            print(f"Role {role_name} already exists")
    db.commit()

def seed_master_data(db: Session):
    # 1. Departments
    departments = [
        {"name": "Engineering", "code": "ENG"},
        {"name": "Human Resources", "code": "HR"},
        {"name": "Finance", "code": "FIN"},
        {"name": "Marketing", "code": "MKT"},
        {"name": "Sales", "code": "SLS"},
        {"name": "Support", "code": "SUP"}
    ]
    for d in departments:
        if not db.query(Department).filter(Department.code == d["code"]).first():
            db.add(Department(name=d["name"], code=d["code"]))
            print(f"Added department: {d['name']}")
    
    # 2. Designations
    designations = [
        {"name": "Frontend Developer", "code": "FE_DEV"},
        {"name": "Backend Developer", "code": "BE_DEV"},
        {"name": "HR Executive", "code": "HR_EXEC"},
        {"name": "HR Manager", "code": "HR_MGR"},
        {"name": "Finance Analyst", "code": "FIN_ANL"}
    ]
    for ds in designations:
        if not db.query(Designation).filter(Designation.code == ds["code"]).first():
            db.add(Designation(name=ds["name"], code=ds["code"]))
            print(f"Added designation: {ds['name']}")
            
    # 3. Shifts
    from datetime import time
    shifts = [
        {
            "name": "General Shift",
            "code": "GEN_SHIFT",
            "start_time": time(9, 0),
            "end_time": time(18, 0),
            "working_hours": 8.0,
            "required_work_minutes": 480,
            "grace_minutes": 15,
            "lunch_duration_minutes": 60,
            "half_day_hours": 4.0,
            "minimum_half_day_minutes": 240,
            "present_hours": 8.0,
            "minimum_present_minutes": 480,
            "late_mark_after_minutes": 15,
            "is_night_shift": False,
            "overtime_allowed": True,
            "max_overtime_minutes": 120,
        },
        {
            "name": "Evening Shift",
            "code": "EVE_SHIFT",
            "start_time": time(14, 0),
            "end_time": time(23, 0),
            "working_hours": 8.0,
            "required_work_minutes": 480,
            "grace_minutes": 20,
            "lunch_duration_minutes": 30,
            "half_day_hours": 4.0,
            "minimum_half_day_minutes": 240,
            "present_hours": 8.0,
            "minimum_present_minutes": 480,
            "late_mark_after_minutes": 20,
            "is_night_shift": False,
            "overtime_allowed": True,
            "max_overtime_minutes": 120,
        },
        {
            "name": "Night Shift",
            "code": "NIGHT_SHIFT",
            "start_time": time(22, 0),
            "end_time": time(7, 0),
            "working_hours": 8.0,
            "required_work_minutes": 480,
            "grace_minutes": 30,
            "lunch_duration_minutes": 40,
            "half_day_hours": 4.0,
            "minimum_half_day_minutes": 240,
            "present_hours": 8.0,
            "minimum_present_minutes": 480,
            "late_mark_after_minutes": 30,
            "is_night_shift": True,
            "overtime_allowed": True,
            "max_overtime_minutes": 120,
        }
    ]
    for s in shifts:
        existing = db.query(Shift).filter(Shift.code == s["code"]).first()
        if not existing:
            # Also try matching by name in case record exists without code
            existing = db.query(Shift).filter(Shift.name == s["name"]).first()
        if not existing:
            db.add(Shift(**s))
            print(f"Added shift: {s['name']}")
        else:
            for k, v in s.items():
                setattr(existing, k, v)
            print(f"Updated shift: {s['name']}")


    # 4. Work Locations
    locations = [
        {"name": "Indore Office", "code": "IND_OFF"},
        {"name": "Remote Home Office", "code": "REMOTE_OFF"},
        {"name": "Hybrid", "code": "HYBRID_OFF"}
    ]
    for loc in locations:
        if not db.query(WorkLocation).filter(WorkLocation.code == loc["code"]).first():
            db.add(WorkLocation(name=loc["name"], code=loc["code"]))
            print(f"Added work location: {loc['name']}")

    # 5. Leave Types
    leave_types = [
        {"name": "Casual Leave", "code": "CL", "unit_type": "full_day", "default_balance_hours": 80.0},
        {"name": "Sick Leave", "code": "SL", "unit_type": "full_day", "default_balance_hours": 40.0},
        {"name": "Half Day", "code": "HD", "unit_type": "half_day", "default_balance_hours": 20.0},
        {"name": "Work From Home", "code": "WFH", "unit_type": "full_day", "default_balance_hours": 120.0},
        {"name": "Comp Off", "code": "CO", "unit_type": "full_day", "default_balance_hours": 16.0}
    ]
    for lt in leave_types:
        if not db.query(LeaveType).filter(LeaveType.code == lt["code"]).first():
            db.add(LeaveType(
                name=lt["name"],
                code=lt["code"],
                unit_type=lt["unit_type"],
                default_balance_hours=lt["default_balance_hours"]
            ))
            print(f"Added leave type: {lt['name']}")

    # 6. Holidays
    holidays = [
        {"holiday_date": date(2026, 1, 1), "name": "New Year's Day"},
        {"holiday_date": date(2026, 8, 15), "name": "Independence Day"},
        {"holiday_date": date(2026, 12, 25), "name": "Christmas Day"}
    ]
    for h in holidays:
        if not db.query(Holiday).filter(Holiday.holiday_date == h["holiday_date"]).first():
            db.add(Holiday(
                holiday_date=h["holiday_date"],
                name=h["name"]
            ))
            print(f"Added holiday: {h['name']}")

    # 7. Document Types & Requirements
    from app.services.document_service import seed_default_document_types, ensure_all_employees_have_requirements
    seed_default_document_types(db)
    ensure_all_employees_have_requirements(db)

    db.commit()
