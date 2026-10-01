from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import Role
from app.models.master_data import Department, Designation, Shift, WorkLocation, LeaveType, Holiday
from datetime import date

def seed_roles(db: Session):
    from sqlalchemy import func
    roles = ["Admin", "HR", "Employee", "Manager"]
    for role_name in roles:
        existing_role = db.query(Role).filter(func.lower(Role.name) == role_name.lower()).first()
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
            "punch_in_grace_minutes": 15,
            "shift_grace_minutes": 15,
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
        {
            "name": "Belagavi ICCC Office",
            "code": "BEL_OFF",
            "location_type": "office",
            "latitude": 15.8716667,
            "longitude": 74.5085833,
            "geofence_radius_meters": 40.0,
            "description": "Belagavi ICCC Office"
        },
        {
            "name": "Hubli ICCC Office",
            "code": "HUB_OFF",
            "location_type": "office",
            "latitude": 15.3547222,
            "longitude": 75.1341667,
            "geofence_radius_meters": 40.0,
            "description": "Hubli ICCC Office"
        },
        {
            "name": "Remote",
            "code": "REMOTE_OFF",
            "location_type": "remote",
            "latitude": None,
            "longitude": None,
            "geofence_radius_meters": 0.0,
            "description": "Remote Working"
        }
    ]
    for loc in locations:
        existing = db.query(WorkLocation).filter(WorkLocation.code == loc["code"]).first()
        if not existing:
            existing = db.query(WorkLocation).filter(WorkLocation.name == loc["name"]).first()
        if not existing:
            db.add(WorkLocation(**loc))
            print(f"Added work location: {loc['name']}")
        else:
            for k, v in loc.items():
                setattr(existing, k, v)
            print(f"Updated work location: {loc['name']}")

    # 5. Leave Types
    leave_types = [
        {"name": "Unpaid Leave", "code": "UL", "unit_type": "full_day", "default_balance_hours": 96.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": False, "is_system_defined": True, "is_editable": False, "is_deletable": False, "annual_entitlement_days": 12.0},
        {"name": "Paid Leave", "code": "PL", "unit_type": "full_day", "default_balance_hours": 144.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": True, "is_system_defined": True, "is_editable": True, "is_deletable": False, "annual_entitlement_days": 18.0},
        {"name": "Casual Leave", "code": "CL", "unit_type": "full_day", "default_balance_hours": 96.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": True, "is_system_defined": False, "is_editable": True, "is_deletable": True, "annual_entitlement_days": 12.0},
        {"name": "Sick Leave", "code": "SL", "unit_type": "full_day", "default_balance_hours": 64.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": True, "is_system_defined": False, "is_editable": True, "is_deletable": True, "annual_entitlement_days": 8.0},
        {"name": "Earned Leave", "code": "EL", "unit_type": "full_day", "default_balance_hours": 144.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": True, "is_system_defined": False, "is_editable": True, "is_deletable": True, "annual_entitlement_days": 18.0},
        {"name": "Half Day", "code": "HD", "unit_type": "half_day", "default_balance_hours": 32.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": True, "is_system_defined": False, "is_editable": True, "is_deletable": True, "annual_entitlement_days": 4.0},
        {"name": "Comp Off", "code": "CO", "unit_type": "full_day", "default_balance_hours": 16.0, "applicable_employee_type": "all", "counts_as_leave": True, "attendance_required": False, "remote_punch_allowed": False, "is_paid": True, "is_system_defined": False, "is_editable": True, "is_deletable": True, "annual_entitlement_days": 2.0}
    ]
    for lt in leave_types:
        existing_lt = db.query(LeaveType).filter((LeaveType.code == lt["code"]) | (func.lower(LeaveType.name) == lt["name"].lower())).first()
        if not existing_lt:
            db.add(LeaveType(**lt))
            print(f"Added leave type: {lt['name']}")
        else:
            for k, v in lt.items():
                setattr(existing_lt, k, v)
            print(f"Updated leave type attributes: {lt['name']}")

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

    # 8. Payroll Master Data & Structures
    seed_payroll_master_data(db)

    db.commit()


def seed_payroll_master_data(db: Session):
    from app.models.payroll import (
        SalaryComponent,
        SalaryStructure,
        SalaryStructureComponent,
        StatutoryConfiguration,
    )

    # 1. Statutory Configurations
    statutory_configs = [
        {
            "code": "PF",
            "name": "Employees Provident Fund (EPF)",
            "employee_rate_pct": 12.0,
            "employer_rate_pct": 12.0,
            "wage_ceiling": 15000.0,
            "calculation_basis": "BASIC",
            "is_enabled": True,
            "description": "Standard 12% employee and employer EPF contribution with ₹15,000 statutory limit",
        },
        {
            "code": "ESI",
            "name": "Employee State Insurance (ESI)",
            "employee_rate_pct": 0.75,
            "employer_rate_pct": 3.25,
            "wage_ceiling": 21000.0,
            "calculation_basis": "GROSS",
            "is_enabled": True,
            "description": "0.75% employee and 3.25% employer contribution for employees earning up to ₹21,000",
        },
        {
            "code": "PT",
            "name": "Professional Tax",
            "employee_rate_pct": 0.0,
            "employer_rate_pct": 0.0,
            "min_wage_threshold": 15000.0,
            "calculation_basis": "GROSS",
            "is_enabled": True,
            "description": "State standard professional tax deduction of ₹200 for gross > ₹15,000",
        },
        {
            "code": "TDS",
            "name": "Tax Deducted at Source (TDS)",
            "employee_rate_pct": 0.0,
            "employer_rate_pct": 0.0,
            "calculation_basis": "TAXABLE",
            "is_enabled": True,
            "description": "Income tax deduction based on projected tax slabs",
        },
    ]
    for sc in statutory_configs:
        existing_sc = db.query(StatutoryConfiguration).filter(StatutoryConfiguration.code == sc["code"]).first()
        if not existing_sc:
            db.add(StatutoryConfiguration(**sc))

    # 2. Standard Salary Components
    components_data = [
        {"code": "BASIC", "name": "Basic Salary", "component_type": "EARNING", "calculation_type": "PERCENTAGE", "calculation_basis": "CTC", "default_value": 50.0, "is_taxable": True, "sequence_order": 1, "description": "Core basic pay component"},
        {"code": "HRA", "name": "House Rent Allowance", "component_type": "EARNING", "calculation_type": "PERCENTAGE", "calculation_basis": "BASIC", "default_value": 40.0, "is_taxable": True, "sequence_order": 2, "description": "Standard accommodation allowance"},
        {"code": "SPECIAL_ALLOWANCE", "name": "Special Allowance", "component_type": "EARNING", "calculation_type": "BALANCE", "calculation_basis": "CTC", "default_value": 0.0, "is_taxable": True, "sequence_order": 3, "description": "Balancing component to fulfill total CTC"},
        {"code": "CONVEYANCE", "name": "Conveyance Allowance", "component_type": "EARNING", "calculation_type": "FIXED", "calculation_basis": None, "default_value": 1600.0, "is_taxable": True, "sequence_order": 4, "description": "Travel and commute allowance"},
        {"code": "MEDICAL", "name": "Medical Allowance", "component_type": "EARNING", "calculation_type": "FIXED", "calculation_basis": None, "default_value": 1250.0, "is_taxable": True, "sequence_order": 5, "description": "Health and medical reimbursement"},
        {"code": "OVERTIME", "name": "Overtime Pay", "component_type": "EARNING", "calculation_type": "HOURLY", "calculation_basis": "HOURLY", "default_value": 0.0, "is_taxable": True, "sequence_order": 6, "description": "Approved overtime hours earnings"},
        {"code": "BONUS", "name": "Bonus", "component_type": "EARNING", "calculation_type": "FIXED", "calculation_basis": None, "default_value": 0.0, "is_taxable": True, "sequence_order": 7, "description": "Performance or festive bonus"},
        {"code": "INCENTIVE", "name": "Incentive", "component_type": "EARNING", "calculation_type": "FIXED", "calculation_basis": None, "default_value": 0.0, "is_taxable": True, "sequence_order": 8, "description": "Monthly variable sales or project incentive"},
        {"code": "PF_EMP", "name": "Employee PF", "component_type": "DEDUCTION", "calculation_type": "PERCENTAGE", "calculation_basis": "BASIC", "default_value": 12.0, "is_taxable": False, "is_statutory": True, "sequence_order": 9, "description": "12% of basic employee PF contribution"},
        {"code": "ESI_EMP", "name": "Employee ESI", "component_type": "DEDUCTION", "calculation_type": "PERCENTAGE", "calculation_basis": "GROSS", "default_value": 0.75, "is_taxable": False, "is_statutory": True, "sequence_order": 10, "description": "0.75% of gross employee health insurance"},
        {"code": "PT", "name": "Professional Tax", "component_type": "DEDUCTION", "calculation_type": "FIXED", "calculation_basis": None, "default_value": 200.0, "is_taxable": False, "is_statutory": True, "sequence_order": 11, "description": "State statutory professional tax"},
        {"code": "TDS", "name": "TDS (Tax)", "component_type": "DEDUCTION", "calculation_type": "FIXED", "calculation_basis": None, "default_value": 0.0, "is_taxable": False, "is_statutory": True, "sequence_order": 12, "description": "Income tax deducted at source"},
        {"code": "LOP", "name": "Loss of Pay (LOP)", "component_type": "DEDUCTION", "calculation_type": "ATTENDANCE", "calculation_basis": "GROSS", "default_value": 0.0, "is_taxable": False, "sequence_order": 13, "description": "Deduction for unapproved leaves and unpaid absences"},
        {"code": "PF_EMPLOYER", "name": "Employer PF", "component_type": "STATUTORY_EMPLOYER", "calculation_type": "PERCENTAGE", "calculation_basis": "BASIC", "default_value": 12.0, "is_taxable": False, "is_statutory": True, "sequence_order": 14, "description": "12% employer matching EPF contribution"},
        {"code": "ESI_EMPLOYER", "name": "Employer ESI", "component_type": "STATUTORY_EMPLOYER", "calculation_type": "PERCENTAGE", "calculation_basis": "GROSS", "default_value": 3.25, "is_taxable": False, "is_statutory": True, "sequence_order": 15, "description": "3.25% employer ESI contribution"},
    ]
    comp_map = {}
    for c in components_data:
        existing_c = db.query(SalaryComponent).filter(SalaryComponent.code == c["code"]).first()
        if not existing_c:
            existing_c = SalaryComponent(**c)
            db.add(existing_c)
            db.flush()
        comp_map[c["code"]] = existing_c

    # 3. Default Salary Structures
    structures_data = [
        {
            "code": "STD_EMP",
            "name": "Standard Employee Structure",
            "salary_basis": "CTC",
            "description": "50% Basic of CTC, 40% HRA of Basic, Special Allowance Balance, Statutory PF & ESI",
            "items": [
                {"code": "BASIC", "calc_type": "PERCENTAGE", "basis": "CTC", "val": 50.0, "seq": 1},
                {"code": "HRA", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 40.0, "seq": 2},
                {"code": "SPECIAL_ALLOWANCE", "calc_type": "BALANCE", "basis": "CTC", "val": 0.0, "seq": 3},
                {"code": "PF_EMP", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 12.0, "seq": 4},
                {"code": "ESI_EMP", "calc_type": "PERCENTAGE", "basis": "GROSS", "val": 0.75, "seq": 5},
                {"code": "PT", "calc_type": "FIXED", "basis": None, "val": 200.0, "seq": 6},
                {"code": "PF_EMPLOYER", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 12.0, "seq": 7},
                {"code": "ESI_EMPLOYER", "calc_type": "PERCENTAGE", "basis": "GROSS", "val": 3.25, "seq": 8},
            ]
        },
        {
            "code": "MGR_STRUCT",
            "name": "Management Structure",
            "salary_basis": "CTC",
            "description": "40% Basic of CTC, 50% HRA of Basic, Fixed Conveyance, Special Allowance Balance",
            "items": [
                {"code": "BASIC", "calc_type": "PERCENTAGE", "basis": "CTC", "val": 40.0, "seq": 1},
                {"code": "HRA", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 50.0, "seq": 2},
                {"code": "CONVEYANCE", "calc_type": "FIXED", "basis": None, "val": 2000.0, "seq": 3},
                {"code": "SPECIAL_ALLOWANCE", "calc_type": "BALANCE", "basis": "CTC", "val": 0.0, "seq": 4},
                {"code": "PF_EMP", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 12.0, "seq": 5},
                {"code": "PT", "calc_type": "FIXED", "basis": None, "val": 200.0, "seq": 6},
                {"code": "PF_EMPLOYER", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 12.0, "seq": 7},
            ]
        },
        {
            "code": "EXEC_STRUCT",
            "name": "Executive (Gross Basis) Structure",
            "salary_basis": "GROSS",
            "description": "Gross Salary Basis: 50% Basic, 40% HRA, Special Allowance Balance",
            "items": [
                {"code": "BASIC", "calc_type": "PERCENTAGE", "basis": "GROSS", "val": 50.0, "seq": 1},
                {"code": "HRA", "calc_type": "PERCENTAGE", "basis": "BASIC", "val": 40.0, "seq": 2},
                {"code": "SPECIAL_ALLOWANCE", "calc_type": "BALANCE", "basis": "GROSS", "val": 0.0, "seq": 3},
                {"code": "PT", "calc_type": "FIXED", "basis": None, "val": 200.0, "seq": 4},
            ]
        }
    ]

    for s in structures_data:
        existing_s = db.query(SalaryStructure).filter(SalaryStructure.code == s["code"]).first()
        if not existing_s:
            existing_s = SalaryStructure(
                code=s["code"],
                name=s["name"],
                salary_basis=s["salary_basis"],
                description=s["description"]
            )
            db.add(existing_s)
            db.flush()

            for item in s["items"]:
                c_obj = comp_map.get(item["code"])
                if c_obj:
                    db.add(SalaryStructureComponent(
                        structure_id=existing_s.id,
                        component_id=c_obj.id,
                        calculation_type=item["calc_type"],
                        calculation_basis=item["basis"],
                        percentage_or_value=item["val"],
                        sequence_order=item["seq"]
                    ))

    db.commit()

